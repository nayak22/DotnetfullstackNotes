import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 — MON =================
d1 = day(1, "MON", "Background Services and Channels",
"Wire up IHostedService and BackgroundService for long-running work inside an ASP.NET Core app, guard workers against crashes, and pass work items between threads with System.Threading.Channels.",
[("IHostedService","Interface with <code>StartAsync</code> and <code>StopAsync</code>; called by the host at application start and shutdown."),
("BackgroundService","Abstract base class implementing <code>IHostedService</code>; you override <code>ExecuteAsync(CancellationToken)</code>."),
("PeriodicTimer","A .NET 6+ timer designed for loops: <code>await timer.WaitForNextTickAsync(ct)</code> skips ticks that were missed instead of piling them up."),
("IServiceScopeFactory","Factory that creates a DI scope; workers are singletons, so they must resolve scoped services (DbContext, repositories) through a fresh scope per unit of work."),
("Channel&lt;T&gt;","A thread-safe, async-first pipe for producer/consumer messaging. <code>Channel.CreateBounded&lt;T&gt;</code> limits backpressure."),
("ChannelWriter&lt;T&gt;","The producer side: <code>TryWrite</code> (non-blocking) or <code>WriteAsync</code> (back-pressure-aware)."),
("ChannelReader&lt;T&gt;","The consumer side: <code>await reader.ReadAsync(ct)</code> or <code>await foreach (var item in reader.ReadAllAsync(ct))</code>."),
("CancellationToken","Propagated from the host's <code>StoppingToken</code>; every async call in a worker should accept and honour it."),
("StoppingToken","The <code>BackgroundService</code> property that is cancelled when the host begins graceful shutdown."),
("IServiceScope","Short-lived DI container child; always disposed in a <code>using</code> block to free scoped resources like <code>DbContext</code>."),
("Never-die error handling","A try/catch around the inner loop so an unexpected exception is logged but the worker restarts rather than crashing the whole app."),
("AddHostedService&lt;T&gt;","Registers a hosted service with the DI container; works for both IHostedService and BackgroundService implementations.")],
["The host calls <code>StartAsync</code> on all hosted services before accepting HTTP requests.",
"<code>ExecuteAsync</code> blocks startup if it doesn't return quickly; await your first real async op immediately.",
"Never inject a <code>DbContext</code> directly into a singleton worker — always create a scope.",
"<code>PeriodicTimer</code> fires one tick at a time; it cannot queue up multiple ticks, so a slow handler doesn't pile up work.",
"Channels replace <code>BlockingCollection&lt;T&gt;</code> (synchronous, thread-blocking); they are async-native and compose well with <code>await</code>.",
"Always call <code>channel.Writer.Complete()</code> when the producer is done so the consumer's <code>ReadAllAsync</code> exits cleanly."],
f'''
<h3>1. IHostedService — the minimum contract</h3>
{C(r"""
// Minimal: implement the two methods yourself
public sealed class StartupNotifier : IHostedService
{
    private readonly ILogger<StartupNotifier> _log;
    public StartupNotifier(ILogger<StartupNotifier> log) => _log = log;

    public Task StartAsync(CancellationToken ct)
    {
        _log.LogInformation("App started at {Time}", DateTimeOffset.UtcNow);
        return Task.CompletedTask;   // synchronous work is fine here
    }

    public Task StopAsync(CancellationToken ct)
    {
        _log.LogInformation("App shutting down");
        return Task.CompletedTask;
    }
}
""", "StartupNotifier.cs")}
{C(r"""
// Register in Program.cs
builder.Services.AddHostedService<StartupNotifier>();
""", "Program.cs")}

<h3>2. BackgroundService with PeriodicTimer</h3>
<p>A common pattern: poll a database table or external API on a schedule without a heavy scheduler library.</p>
{C(r"""
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

public sealed class StockAlertWorker : BackgroundService
{
    private readonly IServiceScopeFactory _scopes;
    private readonly ILogger<StockAlertWorker> _log;

    public StockAlertWorker(IServiceScopeFactory scopes, ILogger<StockAlertWorker> log)
        => (_scopes, _log) = (scopes, log);

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        // Yield immediately so the host finishes starting other services
        await Task.Yield();

        using var timer = new PeriodicTimer(TimeSpan.FromMinutes(5));

        while (await timer.WaitForNextTickAsync(ct))   // returns false when ct is cancelled
        {
            try
            {
                await CheckLowStockAsync(ct);
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                break;   // graceful shutdown
            }
            catch (Exception ex)
            {
                _log.LogError(ex, "StockAlertWorker iteration failed; will retry on next tick");
                // ✓ do NOT rethrow — let the loop continue
            }
        }
    }

    private async Task CheckLowStockAsync(CancellationToken ct)
    {
        await using var scope = _scopes.CreateAsyncScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();

        var low = await db.Products
            .Where(p => p.StockQty < p.ReorderLevel)
            .ToListAsync(ct);

        foreach (var p in low)
            _log.LogWarning("Low stock: {Sku} — {Qty} units left", p.Sku, p.StockQty);
    }
}
""", "StockAlertWorker.cs")}
{warn("Injecting <code>DbContext</code> (or any scoped service) directly into a background worker throws at startup because the worker is a singleton. Always use <code>IServiceScopeFactory</code>.")}

<h3>3. Never-die error handling pattern</h3>
{C(r"""
protected override async Task ExecuteAsync(CancellationToken ct)
{
    while (!ct.IsCancellationRequested)
    {
        try
        {
            await DoWorkLoopAsync(ct);
            // If DoWorkLoopAsync returns normally (should not under normal ops), restart it
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
            break;   // expected during shutdown
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Worker crashed; restarting in 10 s");
            try { await Task.Delay(TimeSpan.FromSeconds(10), ct); }
            catch (OperationCanceledException) { break; }
        }
    }

    async Task DoWorkLoopAsync(CancellationToken innerCt)
    {
        // actual work; may throw any exception
        while (!innerCt.IsCancellationRequested)
        {
            await ProcessNextBatch(innerCt);
        }
    }
}
""", "NeverDiePattern.cs")}
{tip("Log the exception before sleeping, not after. If shutdown happens during the sleep the second log never fires.")}

<h3>4. Channels: producer/consumer queue</h3>
<p>An order import endpoint receives CSV rows; a background worker saves them to SQL Server. The <code>Channel</code> decouples ingestion speed from database write speed.</p>
{C(r"""
// Shared abstraction — register as a singleton
public sealed class OrderImportQueue
{
    private readonly Channel<ImportRow> _channel;
    public ChannelWriter<ImportRow> Writer => _channel.Writer;
    public ChannelReader<ImportRow> Reader => _channel.Reader;

    public OrderImportQueue()
    {
        // BoundedChannelOptions: when full, Writer.WriteAsync waits (backpressure)
        _channel = Channel.CreateBounded<ImportRow>(new BoundedChannelOptions(500)
        {
            FullMode = BoundedChannelFullMode.Wait,
            SingleReader = true
        });
    }
}
""", "OrderImportQueue.cs")}
{C(r"""
// Producer: minimal API endpoint
app.MapPost("/orders/import", async (IFormFile csv, OrderImportQueue queue, CancellationToken ct) =>
{
    using var reader = new StreamReader(csv.OpenReadStream());
    int lineNo = 0;
    while (await reader.ReadLineAsync(ct) is { } line)
    {
        lineNo++;
        if (lineNo == 1) continue;   // skip header
        var parts = line.Split(',');
        if (parts.Length < 3) continue;
        await queue.Writer.WriteAsync(new ImportRow(parts[0], decimal.Parse(parts[1]), int.Parse(parts[2])), ct);
    }
    return Results.Accepted("/orders/import/status");
});
""", "ImportEndpoint.cs")}
{C(r"""
// Consumer: background service
public sealed class OrderImportWorker : BackgroundService
{
    private readonly OrderImportQueue _queue;
    private readonly IServiceScopeFactory _scopes;
    private readonly ILogger<OrderImportWorker> _log;

    public OrderImportWorker(OrderImportQueue queue, IServiceScopeFactory scopes,
        ILogger<OrderImportWorker> log)
        => (_queue, _scopes, _log) = (queue, scopes, log);

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        await foreach (var row in _queue.Reader.ReadAllAsync(ct))
        {
            try
            {
                await using var scope = _scopes.CreateAsyncScope();
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                db.OrderRows.Add(new OrderRow { Sku = row.Sku, UnitPrice = row.UnitPrice, Qty = row.Qty });
                await db.SaveChangesAsync(ct);
            }
            catch (Exception ex)
            {
                _log.LogError(ex, "Failed to persist row {Sku}", row.Sku);
            }
        }
    }
}

public record ImportRow(string Sku, decimal UnitPrice, int Qty);
""", "OrderImportWorker.cs")}

<h3>5. Wiring everything in Program.cs</h3>
{C(r"""
builder.Services.AddSingleton<OrderImportQueue>();
builder.Services.AddHostedService<StockAlertWorker>();
builder.Services.AddHostedService<OrderImportWorker>();
""", "Program.cs")}
{table(["Pattern","When to use"],[
["<code>IHostedService</code>","One-shot startup / shutdown tasks (seed data, warm caches, close resources)"],
["<code>BackgroundService + PeriodicTimer</code>","Polling loops — check every N minutes"],
["<code>BackgroundService + Channel</code>","Queue work from HTTP handlers to a background consumer"],
["Hangfire / Quartz.NET (Tuesday)","Complex scheduling, retries, dashboards, distributed jobs"]])}
''',
["Injecting a scoped service (DbContext) directly into the worker singleton.",
"Letting an unhandled exception in <code>ExecuteAsync</code> bubble up — the host crashes (pre-.NET 6) or the worker silently stops.",
"Not propagating the <code>CancellationToken</code> into every async call; app shutdown hangs for 5 s waiting.",
"Creating a scope in the constructor instead of per work-unit; the scope lives forever and leaks connections.",
"Using <code>Thread.Sleep</code> inside a hosted service instead of <code>await Task.Delay</code>."],
("40 min", [
"Write a <code>HeartbeatWorker</code> that logs the current IST time every 30 seconds using <code>PeriodicTimer</code>. Add a scope around a fake <code>IHeartbeatRepository</code> call so you practise the scope pattern.",
"Create a bounded <code>Channel&lt;string&gt;</code> with capacity 10. Write a producer that writes 20 items (observe back-pressure) and a consumer that processes each with a fake 100 ms delay.",
"Make the channel worker survive a simulated exception on every 5th message without stopping."]),
[("What is the difference between IHostedService and BackgroundService?","IHostedService is the two-method interface. BackgroundService is an abstract implementation that runs ExecuteAsync in the background and wires CancellationToken, StoppingToken and disposal for you."),
("Why use IServiceScopeFactory in a worker?","Workers are singletons; DbContext and other scoped services must not be injected directly (lifetime mismatch). IServiceScopeFactory creates a fresh child container per unit of work, then disposes it."),
("What advantage does PeriodicTimer have over Timer?","It fires one tick at a time and skips missed ticks, so a slow iteration doesn't queue up N pending callbacks. It also integrates naturally with async/await and CancellationToken.")],
[("Basic","What is a background service in ASP.NET Core?","A class that runs alongside the web server in the same process. It implements IHostedService (or BackgroundService). The host starts it before serving HTTP and stops it gracefully on shutdown."),
("Basic","How do you schedule repeated work inside a BackgroundService?","Use <code>PeriodicTimer</code>: create it with the interval, then loop with <code>await timer.WaitForNextTickAsync(ct)</code>. When ct is cancelled the method returns false and the loop exits cleanly."),
("Intermediate","What is System.Threading.Channels and when is it better than a ConcurrentQueue?","Channels add async producer/consumer semantics, back-pressure (bounded) and cooperative cancellation. ConcurrentQueue is sync-only; consuming it requires spinning or blocking. Channels compose naturally with async workflows."),
("Intermediate","How do you gracefully stop a BackgroundService?","The host cancels the BackgroundService.StoppingToken. Any await that accepts it throws OperationCanceledException, which you catch to exit the loop. The host then calls StopAsync and waits (default 5 s) for ExecuteAsync to finish."),
("Intermediate","What is back-pressure and how does BoundedChannel enforce it?","Back-pressure slows the producer when the consumer falls behind. A BoundedChannel with FullMode.Wait makes WriteAsync pause until a slot is free, preventing unlimited memory growth."),
("Advanced","A background worker crashes repeatedly. How do you prevent cascading restarts from flooding the log?","Implement exponential back-off: catch the exception, multiply the delay by 2 each crash up to a maximum (e.g. 60 s), log a warning not an error after the first crash. Reset the delay to minimum after a successful iteration.")])

# ================= DAY 2 — TUE =================
d2 = day(2, "TUE", "Hangfire: Reliable Background Jobs",
"Replace fire-and-forget background threads with Hangfire — durable, retriable, dashboard-visible jobs backed by SQL Server, covering fire-and-forget, delayed, recurring (IST cron), continuations and security.",
[("Hangfire","An open-source library for persistent background job processing in .NET; jobs survive app restarts because they are stored in SQL Server before execution."),
("Storage","Hangfire creates its own schema (HangFire.*) in SQL Server on first run; every job state transition is written there."),
("Fire-and-forget job","A job queued with <code>BackgroundJob.Enqueue</code>; executed once as soon as a worker is free."),
("Delayed job","A job queued with <code>BackgroundJob.Schedule</code>; executed after a specified delay."),
("Recurring job","A job registered with <code>RecurringJob.AddOrUpdate</code>; runs on a cron expression, optionally in a specific timezone."),
("Continuation","A job queued with <code>BackgroundJob.ContinueJobWith</code>; runs after a parent job succeeds."),
("Hangfire Server","The in-process component that polls for due jobs and executes them. <code>app.UseHangfireServer()</code>."),
("Hangfire Dashboard","A middleware-mounted web UI at <code>/hangfire</code> showing queues, jobs and retries. <code>app.UseHangfireDashboard()</code>."),
("Idempotency","Designing a job so that running it twice produces the same result; important because Hangfire may retry on failure."),
("Retry policy","Hangfire retries a failed job up to 10 times by default, with exponential back-off. Configure globally with <code>[AutomaticRetry]</code>."),
("IBackgroundJobClient","DI-injectable interface for enqueueing jobs; preferred over static <code>BackgroundJob</code> in testable code."),
("Quartz.NET","An alternative .NET scheduler with cron-first design, clustered execution and persistent triggers; heavier than Hangfire but more flexible for complex schedules.")],
["Hangfire jobs must be <b>idempotent</b>: on retry the second run should not send two emails or charge twice.",
"Use method expressions (<code>() => service.DoWork(id)</code>), not lambdas with captured objects; Hangfire serialises the method name and arguments, not the closure.",
"The dashboard is public by default — always add an authorization filter in production.",
"Recurring jobs run in UTC internally; convert to IST using <code>TimeZoneInfo</code> in the cron registration.",
"Continuations let you model a pipeline: generate report → send email → archive.",
"Use <code>IBackgroundJobClient</code> and <code>IRecurringJobManager</code> for DI-friendly, testable code."],
f'''
<h3>1. Installing and wiring up Hangfire</h3>
{C(r"""
// NuGet packages needed (add to .csproj):
// <PackageReference Include="Hangfire.AspNetCore" Version="1.8.*" />
// <PackageReference Include="Hangfire.SqlServer" Version="1.8.*" />
""", "packages.txt", lang="text")}
{C(r"""
// Program.cs
builder.Services.AddHangfire(cfg => cfg
    .SetDataCompatibilityLevel(CompatibilityLevel.Version_180)
    .UseSimpleAssemblyNameTypeSerializer()
    .UseRecommendedSerializerSettings()
    .UseSqlServerStorage(builder.Configuration.GetConnectionString("HangfireDb")));

builder.Services.AddHangfireServer();   // starts the in-process worker
""", "Program.cs")}
{C(r"""
// Connection string in appsettings.json
{
  "ConnectionStrings": {
    "HangfireDb": "Server=localhost,1433;Database=SalesHangfire;User Id=sa;Password=YourStrong@Pass;TrustServerCertificate=true"
  }
}
""", "appsettings.json", lang="json")}

<h3>2. Fire-and-forget and delayed jobs</h3>
{C(r"""
// Enqueue: runs as soon as a Hangfire worker picks it up
string jobId = BackgroundJob.Enqueue<IEmailService>(
    svc => svc.SendWelcomeEmailAsync("priya@example.in", "Priya"));

// Delayed: runs 30 minutes after enqueueing
BackgroundJob.Schedule<IEmailService>(
    svc => svc.SendAbandonedCartEmail("ravi@example.in"),
    delay: TimeSpan.FromMinutes(30));

// Injected client (preferred — testable)
public class OrderController(IBackgroundJobClient jobs)
{
    [HttpPost]
    public IActionResult PlaceOrder(OrderRequest req)
    {
        var orderId = SaveOrder(req);
        jobs.Enqueue<IInvoiceService>(svc => svc.GenerateInvoice(orderId));
        return Ok(orderId);
    }
}
""", "OrderController.cs")}

<h3>3. Recurring jobs with IST timezone</h3>
{C(r"""
// In Program.cs after app.Build()
var ist = TimeZoneInfo.FindSystemTimeZoneById("India Standard Time");

RecurringJob.AddOrUpdate<IDailySalesJob>(
    "daily-sales-report",
    job => job.RunAsync(),
    Cron.Daily(hour: 8, minute: 0),   // 08:00 IST every day
    new RecurringJobOptions { TimeZone = ist });

RecurringJob.AddOrUpdate<IStockReconciler>(
    "stock-reconcile",
    job => job.RunAsync(),
    "0 */4 * * *",    // every 4 hours
    new RecurringJobOptions { TimeZone = ist });
""", "RecurringSetup.cs")}
{tip("Use <code>Cron.Never()</code> to disable a recurring job without removing it — handy for disabling in staging.")}

<h3>4. Continuations: pipeline jobs</h3>
{C(r"""
// Generate report → email it → archive it
string reportJobId = BackgroundJob.Enqueue<IReportService>(
    svc => svc.GenerateMonthlyReport(2026, 11));

string emailJobId = BackgroundJob.ContinueJobWith<IEmailService>(
    reportJobId,
    svc => svc.SendReportEmail("cfo@acme.in", reportJobId));

BackgroundJob.ContinueJobWith<IArchiveService>(
    emailJobId,
    svc => svc.ArchiveReport(reportJobId));
""", "PipelineJobs.cs")}

<h3>5. Securing the dashboard</h3>
{C(r"""
// Local-only: only allow requests from 127.0.0.1
app.UseHangfireDashboard("/hangfire", new DashboardOptions
{
    Authorization = new[] { new LocalRequestsOnlyAuthorizationFilter() }
});

// Role-based (production)
app.UseHangfireDashboard("/hangfire", new DashboardOptions
{
    Authorization = new[] { new HangfireRoleAuthFilter("Admin") }
});

public sealed class HangfireRoleAuthFilter : IDashboardAuthorizationFilter
{
    private readonly string _role;
    public HangfireRoleAuthFilter(string role) => _role = role;

    public bool Authorize(DashboardContext ctx)
    {
        var http = ctx.GetHttpContext();
        return http.User.Identity?.IsAuthenticated == true && http.User.IsInRole(_role);
    }
}
""", "DashboardAuth.cs")}

<h3>6. Retry attributes and idempotency</h3>
{C(r"""
[AutomaticRetry(Attempts = 3, OnAttemptsExceeded = AttemptsExceededAction.Delete)]
public async Task SendWelcomeEmailAsync(string to, string name)
{
    // Idempotency: check whether the email was already sent
    if (await _emailLog.AlreadySentAsync(to, "welcome"))
        return;   // second run is a no-op

    await _mailer.SendAsync(to, subject: $"Welcome, {name}!", body: BuildBody(name));
    await _emailLog.MarkSentAsync(to, "welcome");
}
""", "EmailService.cs")}
{table(["Job type","API","Use case"],[
["Fire-and-forget","<code>BackgroundJob.Enqueue</code>","Invoice PDF after payment"],
["Delayed","<code>BackgroundJob.Schedule</code>","Abandoned cart reminder 30 min later"],
["Recurring","<code>RecurringJob.AddOrUpdate</code>","Daily 08:00 IST sales report"],
["Continuation","<code>BackgroundJob.ContinueJobWith</code>","Generate → email → archive pipeline"],
["Batch (Pro)","<code>BatchJob.StartNew</code>","Process 10 000 rows, fan-out / fan-in"]])}
''',
["Capturing <code>this</code> in the method expression — Hangfire serialises the type and method name, not the instance; inject the service by its interface instead.",
"Not making jobs idempotent and triggering duplicate emails or duplicate charges on retry.",
"Leaving the dashboard open to anonymous requests.",
"Using <code>Thread.Sleep</code> in a job — always use <code>await Task.Delay</code> (Hangfire jobs are async-aware).",
"Forgetting to call <code>app.UseHangfireServer()</code>; jobs are stored but never executed."],
("40 min", [
"Add Hangfire to the Week 20 auth service project (locally). Enqueue a fire-and-forget job to 'send a registration email' (just log) when a user registers. Confirm it appears in the dashboard.",
"Set up a recurring job that logs the current INR/USD exchange rate placeholder at 09:00 IST every weekday.",
"Write an idempotency check using an in-memory dictionary: if the job key was already processed, return early."]),
[("What makes a Hangfire job durable?","It is serialised to SQL Server before the worker picks it up. If the app crashes after enqueueing but before execution, the job is still in the database and will run when the app restarts."),
("What is the default retry behaviour?","Hangfire retries up to 10 times with exponential back-off (around 1 min, 4 min, 10 min…). Override with <code>[AutomaticRetry(Attempts = 3)]</code>."),
("BackgroundService vs Hangfire?","BackgroundService is built-in and good for continuous workers (polling, channels). Hangfire adds persistence, retries, cron scheduling, a dashboard and distributed execution across multiple app instances.")],
[("Basic","What is Hangfire and what problem does it solve?","Hangfire is a persistent background job library. It solves the problem of tasks lost on app crash: every job is written to SQL Server before execution, so it survives restarts."),
("Basic","What is a recurring job in Hangfire?","A job registered with RecurringJob.AddOrUpdate that fires on a cron schedule. Hangfire stores the last run time and next due time in SQL Server and handles timezone conversion."),
("Intermediate","How does Hangfire differ from Quartz.NET?","Hangfire is simpler to set up, has a built-in dashboard and suits most apps. Quartz.NET is more powerful for complex schedules (misfire policies, clustered triggers, job stores) and suits enterprise scheduling needs."),
("Intermediate","How do you make a Hangfire job idempotent?","Before doing the real work, check a durable log (a database flag, a Redis key) to see if this exact operation was already completed; if so, return early. The check-and-mark must be in the same transaction or use compare-and-swap."),
("Intermediate","Explain Hangfire continuations.","A continuation is a job that is enqueued only after its parent job succeeds. Chain them with BackgroundJob.ContinueJobWith(parentJobId, ...). If the parent fails, the continuation is never started."),
("Advanced","How would you run Hangfire workers in a separate microservice?","Install Hangfire.SqlServer in both the web app (storage only, no server) and a dedicated worker process (server only). Both share the same SQL Server database. The web app enqueues; the worker processes. Scale the worker independently.")])

# ================= DAY 3 — WED =================
d3 = day(3, "WED", "Sending Email with MailKit",
"Send plain-text and HTML emails using MailKit, test locally with Mailpit in Docker, build a reusable IEmailSender service, and keep credentials in user-secrets.",
[("MailKit","A cross-platform .NET library for SMTP, IMAP and POP3; the recommended replacement for <code>System.Net.Mail.SmtpClient</code> which is deprecated for async use."),
("MimeMessage","MailKit's message class. Set <code>From</code>, <code>To</code>, <code>Subject</code> and <code>Body</code> (via <code>BodyBuilder</code>)."),
("BodyBuilder","A helper inside MailKit for building multipart messages: <code>HtmlBody</code> and <code>TextBody</code> together create a <code>multipart/alternative</code> body so plain-text clients get readable text."),
("SmtpClient (MailKit)","<code>MailKit.Net.Smtp.SmtpClient</code> — not the same as <code>System.Net.Mail.SmtpClient</code>. Always use the MailKit one."),
("STARTTLS","A protocol upgrade that starts on the plain port (587) and upgrades to TLS. MailKit uses <code>SecureSocketOptions.StartTls</code>."),
("Mailpit","A local SMTP fake server with a web UI at port 8025; catches emails instead of sending them. Replaces smtp4dev; both work fine."),
("smtp4dev","Another popular local SMTP trap. Docker image: <code>rnwood/smtp4dev</code>."),
("User-secrets","<code>dotnet user-secrets set</code> stores credentials outside source control in <code>%APPDATA%/Microsoft/UserSecrets</code>."),
("IEmailSender","A custom interface (or ASP.NET Core Identity's built-in one) that abstracts sending; lets you swap MailKit for SendGrid in tests or staging."),
("EmailOptions","A strongly typed options class for SMTP host, port, sender address and credentials — bound via <code>builder.Services.Configure&lt;EmailOptions&gt;</code>.")],
["<code>System.Net.Mail.SmtpClient</code> lacks a proper async implementation; it blocks a thread pool thread. Always use MailKit.",
"Always build a <code>multipart/alternative</code> body (<code>BodyBuilder.HtmlBody</code> + <code>BodyBuilder.TextBody</code>) so email clients that don't render HTML still show something.",
"Use a <code>using</code> block for <code>MailKit.Net.Smtp.SmtpClient</code>; it owns a socket.",
"Keep SMTP passwords in user-secrets or Azure Key Vault, never in appsettings.json checked into Git.",
"Test locally with Mailpit (port 1025 SMTP, 8025 web UI) before connecting to a real relay.",
"For production in India common choices are AWS SES (cheapest), SendGrid, or Brevo (formerly Sendinblue)."],
f'''
<h3>1. Why not System.Net.Mail?</h3>
{table(["","System.Net.Mail.SmtpClient","MailKit SmtpClient"],[
["Truly async","No (fake async wraps sync)","Yes"],
["HTML + text multipart","Clunky","BodyBuilder handles it"],
["IMAP / POP3","No","Yes"],
["Maintained","Deprecated","Active (David Howarth)"],
["NuGet package","BCL (no package)","<code>MailKit</code>"]])}

<h3>2. NuGet package</h3>
{C(r"""
// Add to your .csproj
// <PackageReference Include="MailKit" Version="4.7.*" />
""", "packages.txt", lang="text")}

<h3>3. Sending a basic email</h3>
{C(r"""
using MailKit.Net.Smtp;
using MailKit.Security;
using MimeKit;

var message = new MimeMessage();
message.From.Add(new MailboxAddress("Sales Bot", "noreply@acme.in"));
message.To.Add(new MailboxAddress("Amit Sharma", "amit@example.in"));
message.Subject = "Invoice #INV-2026-1042 — ₹14,750";

var builder = new BodyBuilder
{
    HtmlBody = "<h2>Invoice #INV-2026-1042</h2><p>Amount: <b>₹14,750</b></p>",
    TextBody  = "Invoice #INV-2026-1042\nAmount: Rs. 14,750"
};
message.Body = builder.ToMessageBody();

using var smtp = new SmtpClient();                           // MailKit.Net.Smtp.SmtpClient
await smtp.ConnectAsync("localhost", 1025, SecureSocketOptions.None);  // Mailpit
await smtp.SendAsync(message);
await smtp.DisconnectAsync(quit: true);
""", "BasicEmail.cs")}

<h3>4. Options + user-secrets</h3>
{C(r"""
// EmailOptions.cs
public sealed class EmailOptions
{
    public const string Section = "Email";
    public string Host     { get; set; } = "localhost";
    public int    Port     { get; set; } = 587;
    public bool   UseSsl   { get; set; } = false;
    public string From     { get; set; } = "noreply@acme.in";
    public string FromName { get; set; } = "Acme Sales";
    public string? Username { get; set; }
    public string? Password { get; set; }
}
""", "EmailOptions.cs")}
{C(r"""
// Store secrets locally (never commit passwords)
// dotnet user-secrets init
// dotnet user-secrets set "Email:Username" "smtp_user"
// dotnet user-secrets set "Email:Password" "smtp_pass"

// Program.cs
builder.Services.Configure<EmailOptions>(builder.Configuration.GetSection(EmailOptions.Section));
""", "Program.cs")}
{C(r"""
// appsettings.json (safe to commit — no credentials)
{
  "Email": {
    "Host": "smtp.sendgrid.net",
    "Port": 587,
    "UseSsl": false,
    "From": "noreply@acme.in",
    "FromName": "Acme Sales"
  }
}
""", "appsettings.json", lang="json")}

<h3>5. IEmailSender service</h3>
{C(r"""
// IEmailSender.cs
public interface IEmailSender
{
    Task SendAsync(string to, string toName, string subject, string htmlBody, string? textBody = null,
        CancellationToken ct = default);
}
""", "IEmailSender.cs")}
{C(r"""
// MailKitEmailSender.cs
using MailKit.Net.Smtp;
using MailKit.Security;
using Microsoft.Extensions.Options;
using MimeKit;

public sealed class MailKitEmailSender : IEmailSender
{
    private readonly EmailOptions _opt;
    private readonly ILogger<MailKitEmailSender> _log;

    public MailKitEmailSender(IOptions<EmailOptions> opt, ILogger<MailKitEmailSender> log)
        => (_opt, _log) = (opt.Value, log);

    public async Task SendAsync(string to, string toName, string subject,
        string htmlBody, string? textBody = null, CancellationToken ct = default)
    {
        var msg = new MimeMessage();
        msg.From.Add(new MailboxAddress(_opt.FromName, _opt.From));
        msg.To.Add(new MailboxAddress(toName, to));
        msg.Subject = subject;

        var body = new BodyBuilder { HtmlBody = htmlBody };
        if (!string.IsNullOrWhiteSpace(textBody))
            body.TextBody = textBody;
        msg.Body = body.ToMessageBody();

        using var smtp = new SmtpClient();
        await smtp.ConnectAsync(_opt.Host, _opt.Port,
            _opt.UseSsl ? SecureSocketOptions.SslOnConnect : SecureSocketOptions.StartTlsWhenAvailable, ct);

        if (!string.IsNullOrEmpty(_opt.Username))
            await smtp.AuthenticateAsync(_opt.Username, _opt.Password, ct);

        await smtp.SendAsync(msg, ct);
        await smtp.DisconnectAsync(quit: true, ct);

        _log.LogInformation("Email sent to {To} subject {Subject}", to, subject);
    }
}
""", "MailKitEmailSender.cs")}
{C(r"""
// Register in Program.cs
builder.Services.AddSingleton<IEmailSender, MailKitEmailSender>();
""", "Program.cs")}

<h3>6. Local Mailpit via Docker Compose</h3>
{C(r"""
# docker-compose.yml (add to the project root)
services:
  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI  → http://localhost:8025
    restart: unless-stopped
""", "docker-compose.yml", lang="yaml")}
{C(r"""
# Start
docker compose up -d mailpit

# View captured emails
open http://localhost:8025
""", "run.sh", lang="bash")}
{tip("Set <code>Email:Host=localhost</code> and <code>Email:Port=1025</code> in <code>appsettings.Development.json</code>; Mailpit catches everything without TLS or auth.")}

<h3>7. Simple HTML template</h3>
{C(r"""
public static class EmailTemplates
{
    public static string SalesReport(string recipientName, decimal totalSales,
        int orderCount, DateOnly date) => $QQQ
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <h2 style="color:#1a3c6e">Daily Sales Report &mdash; {date:dd MMM yyyy}</h2>
          <p>Hi {recipientName},</p>
          <table style="border-collapse:collapse;width:100%">
            <tr style="background:#f0f4fa">
              <th style="padding:8px;text-align:left">Metric</th>
              <th style="padding:8px;text-align:right">Value</th>
            </tr>
            <tr>
              <td style="padding:8px">Total Sales</td>
              <td style="padding:8px;text-align:right">Rs. {totalSales:N2}</td>
            </tr>
            <tr style="background:#f0f4fa">
              <td style="padding:8px">Orders</td>
              <td style="padding:8px;text-align:right">{orderCount}</td>
            </tr>
          </table>
          <p style="color:#666;font-size:12px">Auto-generated by Acme Sales System</p>
        </body>
        </html>
        QQQ;
}
""", "EmailTemplates.cs")}
''',
["Using <code>System.Net.Mail.SmtpClient</code> — it fakes async; use MailKit.",
"Sending only an HTML body; always include a <code>TextBody</code> fallback.",
"Hard-coding credentials in appsettings.json and committing to Git.",
"Not disposing the MailKit <code>SmtpClient</code>; leaves TCP connections open.",
"Forgetting <code>quit: true</code> in <code>DisconnectAsync</code>; some SMTP servers keep the connection open and block."],
("40 min", [
"Set up Mailpit with Docker Compose. Configure <code>EmailOptions</code> in <code>appsettings.Development.json</code> (host <code>localhost</code>, port <code>1025</code>).",
"Implement <code>IEmailSender</code> and send a test email from a minimal API endpoint. Verify it appears in the Mailpit web UI at <code>http://localhost:8025</code>.",
"Add an HTML template for a 'Your order has shipped' email with order ID, items (HTML table) and total in ₹."]),
[("Why use MailKit over System.Net.Mail?","System.Net.Mail.SmtpClient.SendMailAsync is a fake async that blocks a thread pool thread and is marked as not recommended in its own XML docs. MailKit has a true async implementation, active maintenance and richer features."),
("How do you send both HTML and plain text?","Use BodyBuilder: set both HtmlBody and TextBody, then call ToMessageBody(). MimeKit automatically wraps them in a multipart/alternative MIME part so the email client picks what it can render."),
("How do you keep SMTP credentials out of source control?","Use dotnet user-secrets (development) or environment variables / Azure Key Vault (production). The IOptions pattern reads from either source transparently.")],
[("Basic","Why is System.Net.Mail.SmtpClient deprecated?","Its SendMailAsync is not truly asynchronous — it uses Task.Factory.FromAsync wrapping a sync implementation, blocking a thread. It is not being improved. MailKit is the recommended replacement."),
("Basic","What is Mailpit and how do you use it for local testing?","A local SMTP trap that accepts all email and shows it in a web UI. Run it with Docker on port 1025 (SMTP) and 8025 (UI). Point the app's SMTP host to localhost:1025; no credentials needed."),
("Intermediate","What is a multipart/alternative MIME message?","A message containing the same content in multiple formats — typically text/html and text/plain — so the client chooses the best one. MailKit's BodyBuilder creates this automatically when you set both HtmlBody and TextBody."),
("Intermediate","How do you configure different SMTP settings per environment?","Use appsettings.json for defaults, appsettings.Development.json to override with Mailpit settings, and user-secrets or Key Vault for credentials. IOptions picks up the merged configuration automatically."),
("Intermediate","How would you send bulk email without blocking the web server?","Enqueue a Hangfire fire-and-forget or recurring job that calls IEmailSender per recipient. The HTTP request returns immediately; the worker processes the queue in the background."),
("Advanced","How do you add an email attachment from a MemoryStream?","Call builder.Attachments.Add(fileName, stream, ContentType.Parse(mimeType)) before ToMessageBody(). For large files, stream from disk with a FileStream to avoid loading everything into memory.")])

# ================= DAY 4 — THU =================
d4 = day(4, "THU", "SignalR Hubs",
"Build a real-time server with ASP.NET Core SignalR — hubs, strongly typed clients, groups, connection lifecycle, and IHubContext for pushing from background services.",
[("SignalR","An ASP.NET Core abstraction over WebSockets (falling back to Server-Sent Events / long polling) for real-time bidirectional communication."),
("Hub","The server-side class that handles connections and receives client messages; inherits <code>Hub</code> or <code>Hub&lt;T&gt;</code>."),
("Hub&lt;T&gt;","A strongly typed hub where T is a client-proxy interface; <code>Clients.All.Method()</code> is checked at compile time."),
("HubContext","<code>IHubContext&lt;THub&gt;</code> or <code>IHubContext&lt;THub,T&gt;</code> injected into controllers or background services to push messages without an active connection."),
("Clients.All","Sends a message to every connected client."),
("Clients.Caller","Sends only to the client that invoked the current hub method."),
("Clients.Others","Sends to all clients except the caller."),
("Clients.Group","Sends to all clients that joined a named group."),
("Clients.User","Sends to all connections for a given user identifier."),
("Groups","Named collections of connections; a client can be in multiple groups. <code>Groups.AddToGroupAsync</code> / <code>RemoveFromGroupAsync</code>."),
("OnConnectedAsync","Hub override called when a client connects; use it to join groups or track online users."),
("OnDisconnectedAsync","Hub override called on disconnect; <code>exception</code> is null for clean disconnects."),
("MapHub","<code>app.MapHub&lt;ChatHub&gt;(\"/chathub\")</code> wires the hub to a URL.")],
["SignalR uses WebSockets when available; it falls back automatically without any code change.",
"Hub instances are created <b>per method invocation</b>, not per connection — don't store connection state in hub fields.",
"Store per-connection state in <code>Context.Items</code> or in a singleton dictionary keyed by <code>Context.ConnectionId</code>.",
"Strongly typed hubs (<code>Hub&lt;T&gt;</code>) catch typos in method names at compile time.",
"<code>IHubContext</code> is the right way to push from a background job or Hangfire worker; never try to inject a Hub directly.",
"Groups are in-memory and local to the server instance; for multi-server scale-out you need a Redis or Azure SignalR backplane."],
f'''
<h3>1. A minimal chat hub</h3>
{C(r"""
using Microsoft.AspNetCore.SignalR;

// Map in Program.cs: app.MapHub<ChatHub>("/chathub");
public sealed class ChatHub : Hub
{
    // Called by the client: connection.invoke("SendMessage", room, message)
    public async Task SendMessage(string room, string message)
    {
        // Broadcast to everyone in the group named after the room
        await Clients.Group(room).SendAsync("ReceiveMessage",
            Context.User?.Identity?.Name ?? Context.ConnectionId,
            message,
            DateTime.UtcNow);
    }

    public async Task JoinRoom(string room)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, room);
        await Clients.Group(room).SendAsync("UserJoined",
            Context.User?.Identity?.Name ?? "anonymous", room);
    }

    public async Task LeaveRoom(string room)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, room);
        await Clients.Group(room).SendAsync("UserLeft",
            Context.User?.Identity?.Name ?? "anonymous", room);
    }

    public override async Task OnConnectedAsync()
    {
        await base.OnConnectedAsync();
        // e.g. track the connection in a singleton service
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        if (exception is not null)
            // log unexpected disconnect
            ;
        await base.OnDisconnectedAsync(exception);
    }
}
""", "ChatHub.cs")}
{C(r"""
// Program.cs
builder.Services.AddSignalR();
// ...
app.MapHub<ChatHub>("/chathub");
""", "Program.cs")}

<h3>2. Strongly typed hub (Hub&lt;T&gt;)</h3>
{C(r"""
// Client contract — interface that describes messages the SERVER pushes to CLIENTS
public interface IChatClient
{
    Task ReceiveMessage(string user, string message, DateTime at);
    Task UserJoined(string user, string room);
    Task UserLeft(string user, string room);
    Task ReceiveTyping(string user);
}

// Strongly typed hub: Clients.All is IChatClient — compile-time checked
public sealed class ChatHub : Hub<IChatClient>
{
    public async Task SendMessage(string room, string message)
    {
        await Clients.Group(room).ReceiveMessage(
            Context.User!.Identity!.Name!, message, DateTime.UtcNow);
        // Clients.Group(room).ReceiveMesage(...) ← compile error: typo caught!
    }

    public async Task Typing(string room)
    {
        await Clients.OthersInGroup(room).ReceiveTyping(
            Context.User!.Identity!.Name!);
    }

    public async Task JoinRoom(string room)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, room);
        await Clients.Group(room).UserJoined(Context.User!.Identity!.Name!, room);
    }
}
""", "StronglyTypedHub.cs")}

<h3>3. IHubContext — push from a background service</h3>
{C(r"""
// Push a price update from a Hangfire job or background worker
public sealed class PriceUpdateJob
{
    private readonly IHubContext<ChatHub, IChatClient> _hub;
    public PriceUpdateJob(IHubContext<ChatHub, IChatClient> hub) => _hub = hub;

    // Called by Hangfire every minute
    public async Task RunAsync()
    {
        decimal price = await FetchLatestPriceAsync();   // call a price API or DB
        // Send to ALL connected clients — no connection needed
        await _hub.Clients.All.ReceiveMessage("PriceBot",
            $"HDFC Bank: ₹{price:N2}", DateTime.UtcNow);
    }
}
""", "PriceUpdateJob.cs")}
{tip("Register <code>PriceUpdateJob</code> as a transient or use <code>IServiceScopeFactory</code> inside a background service. <code>IHubContext</code> is a singleton so it's safe to inject directly into a singleton worker.")}

<h3>4. Connection events and groups</h3>
{C(r"""
// Track online users across connections with a singleton
public sealed class OnlineTracker
{
    private readonly Dictionary<string, string> _conToUser = new();
    public void Add(string connectionId, string userName)    => _conToUser[connectionId] = userName;
    public void Remove(string connectionId)                  => _conToUser.Remove(connectionId);
    public IReadOnlyCollection<string> Users                 => _conToUser.Values.Distinct().ToList();
}

// In the hub
public sealed class ChatHub : Hub<IChatClient>
{
    private readonly OnlineTracker _tracker;
    public ChatHub(OnlineTracker tracker) => _tracker = tracker;

    public override async Task OnConnectedAsync()
    {
        _tracker.Add(Context.ConnectionId, Context.User?.Identity?.Name ?? "anon");
        await Clients.All.UserJoined(Context.User?.Identity?.Name ?? "anon", "global");
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _tracker.Remove(Context.ConnectionId);
        await Clients.All.UserLeft(Context.User?.Identity?.Name ?? "anon", "global");
        await base.OnDisconnectedAsync(exception);
    }
}
""", "OnlineTracker.cs")}

<h3>5. MapHub and middleware order</h3>
{C(r"""
// Order matters: auth middleware must come before MapHub
var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.MapHub<ChatHub>("/chathub");
app.MapHub<NotificationHub>("/notifications");
""", "Program.cs")}
{table(["Clients property","Who receives the message"],[
["<code>Clients.All</code>","Every connected client"],
["<code>Clients.Caller</code>","Only the client that called the hub method"],
["<code>Clients.Others</code>","Everyone except the caller"],
["<code>Clients.Group(name)</code>","All clients in the named group"],
["<code>Clients.OthersInGroup(name)</code>","Group members except the caller"],
["<code>Clients.User(userId)</code>","All connections for that user identifier"],
["<code>Clients.Client(connectionId)</code>","Exactly one connection"]])}
''',
["Storing connection-specific state in Hub fields — hub instances are transient (new per call).",
"Using IHubContext inside a Scoped or Transient DI service when it must outlive the request.",
"Calling <code>Clients.All.SendAsync(\"methodName\", ...)</code> with a strongly typed hub — use the interface method directly.",
"Forgetting <code>app.UseAuthentication()</code> before <code>app.MapHub</code>; <code>Context.User</code> is always anonymous.",
"Putting scale-out-sensitive logic in a singleton OnlineTracker without a Redis backplane."],
("40 min", [
"Scaffold a new <code>WebApplication</code> project, add <code>AddSignalR()</code>, and create a <code>NotificationHub : Hub</code>. Add a <code>Broadcast(string message)</code> method that pushes to <code>Clients.All</code>.",
"Create a strongly typed hub interface <code>INotificationClient</code> with a <code>Notify(string msg, string level)</code> method and migrate the hub to <code>Hub&lt;INotificationClient&gt;</code>.",
"Inject <code>IHubContext&lt;NotificationHub, INotificationClient&gt;</code> into a background service that pushes a heartbeat message every 10 seconds."]),
[("Why are Hub instances created per invocation?","To keep hubs stateless and thread-safe. The connection context (Context, Clients, Groups) is injected fresh per call. Storing state in fields would be a data race with concurrent calls."),
("What is the difference between Clients.Others and Clients.OthersInGroup?","Clients.Others excludes the caller from the entire server. Clients.OthersInGroup excludes the caller only within a named group; members outside that group are unaffected."),
("How do you push from outside a hub?","Inject IHubContext<THub> (or IHubContext<THub,TClient> for strongly typed) into any service or controller; call its Clients property the same way you would inside the hub.")],
[("Basic","What transport does SignalR use?","WebSockets (preferred), then Server-Sent Events, then long polling. The client and server negotiate the best available transport automatically."),
("Basic","What is the difference between Hub and Hub&lt;T&gt;?","Hub exposes dynamic Clients where you call SendAsync with a string method name. Hub&lt;T&gt; uses a client proxy interface for compile-time safety — typos and wrong signatures become build errors."),
("Intermediate","How do groups work in SignalR?","Groups are named collections of connection IDs managed by the SignalR server. Add a connection with Groups.AddToGroupAsync; remove with RemoveFromGroupAsync. Groups exist only in memory (or in a backplane for multi-server)."),
("Intermediate","Hub instance lifetime vs connection lifetime?","A new Hub instance is created for each invoked method (a few milliseconds). A connection lives for the duration of the WebSocket or SSE session (seconds to hours). Store connection state in a singleton or in Context.Items, not in hub fields."),
("Intermediate","How do you push from a Hangfire job to SignalR clients?","Inject IHubContext<THub, TClient> into the job class. Because IHubContext is a singleton it is safe to hold. Call Clients.All.Method() or Clients.User(id).Method() without needing an active hub method."),
("Advanced","What is a SignalR backplane and when is it needed?","A backplane (Redis, Azure SignalR Service) synchronises group membership and messages across multiple server instances. Without one, Clients.All only reaches clients connected to the same server.")])

# ================= DAY 5 — FRI =================
d5 = day(5, "FRI", "SignalR Authentication and Advanced Features",
"Secure SignalR hubs with JWT, target individual users, map connection IDs to user identities, tune keep-alive and timeouts, and understand the access_token query-string pattern.",
[("OnMessageReceived","A JWT Bearer event handler that reads the token from the query string instead of the Authorization header — required for WebSocket/SSE connections."),
("[Authorize] on a hub","Requires the caller to be authenticated; works with any ASP.NET Core auth scheme."),
("IUserIdProvider","Interface that maps a ClaimsPrincipal to a user identifier used by <code>Clients.User(id)</code>."),
("Clients.User(id)","Sends to all connections for the given user ID (from IUserIdProvider). Used for direct messages and user-scoped notifications."),
("KeepAliveInterval","How often the server sends a ping to verify the connection is alive. Default: 15 s."),
("ClientTimeoutInterval","How long the server waits after the last received message before treating the connection as dead. Default: 30 s. Should be at least 2× KeepAliveInterval."),
("ServerTimeout","Client-side counterpart; how long the client waits for a ping before reconnecting. Keep greater than KeepAliveInterval."),
("withAutomaticReconnect","JavaScript client option to reconnect automatically with configurable back-off."),
("HubException","A safe exception thrown inside a hub method; the message is serialised to the client. Other exceptions are swallowed by default (only a generic error is sent)."),
("connection_map","A per-hub singleton (or distributed store) mapping user IDs to their active connection IDs for direct targeting.")],
["WebSocket connections cannot send custom HTTP headers; the JWT must travel via the <code>access_token</code> query parameter and be pulled in <code>OnMessageReceived</code>.",
"Use <code>[Authorize]</code> on the hub class to block anonymous connections, not just on individual methods.",
"<code>Clients.User(userId)</code> works across multiple connections for the same user (e.g. two browser tabs).",
"Only throw <code>HubException</code> from hub methods — the message text is sent to the client. Other exception messages are hidden by default for security.",
"Increase <code>MaximumReceiveMessageSize</code> for large binary uploads; default is 32 KB.",
"For true 1-on-1 DMs, store the target's current connection IDs in a <code>ConcurrentDictionary</code> and use <code>Clients.Client(connectionId)</code>."],
f'''
<h3>1. JWT access_token query-string pattern</h3>
{C(r"""
// Program.cs — configure JWT Bearer to read from ?access_token=... for SignalR
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(opt =>
    {
        opt.TokenValidationParameters = new TokenValidationParameters { /* same as your API */ };

        // SignalR WebSocket/SSE can't send Authorization header
        opt.Events = new JwtBearerEvents
        {
            OnMessageReceived = ctx =>
            {
                var accessToken = ctx.Request.Query["access_token"];
                var path = ctx.HttpContext.Request.Path;

                if (!string.IsNullOrEmpty(accessToken) &&
                    path.StartsWithSegments("/chathub"))   // only for SignalR endpoints
                {
                    ctx.Token = accessToken;   // set the token from the query string
                }
                return Task.CompletedTask;
            }
        };
    });
""", "Program.cs")}
{warn("Tokens in query strings appear in server logs and browser history. For production consider short-lived one-time SignalR access tokens (e.g. from Azure SignalR) rather than your main JWT.", "Security note")}

<h3>2. [Authorize] on a hub</h3>
{C(r"""
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.SignalR;

[Authorize]   // entire hub requires authentication
public sealed class ChatHub : Hub<IChatClient>
{
    // All methods inherit the [Authorize] requirement
    public Task SendMessage(string room, string msg) => /* ... */ Task.CompletedTask;

    // Individual methods can add further restrictions
    [Authorize(Roles = "Admin")]
    public Task Broadcast(string msg) => Clients.All.ReceiveMessage("admin", msg, DateTime.UtcNow);
}
""", "AuthChatHub.cs")}
{C(r"""
// In Program.cs — middleware order is critical
app.UseAuthentication();   // 1st: populates HttpContext.User
app.UseAuthorization();    // 2nd: enforces [Authorize]
app.MapHub<ChatHub>("/chathub");  // 3rd: SignalR endpoints
""", "Program.cs")}

<h3>3. IUserIdProvider — custom user identifier</h3>
{C(r"""
// By default SignalR uses the NameIdentifier claim as the user ID.
// Override if your JWT uses a different claim (e.g. "sub", "email").
public sealed class EmailUserIdProvider : IUserIdProvider
{
    public string? GetUserId(HubConnectionContext connection) =>
        connection.User?.FindFirst("email")?.Value
        ?? connection.User?.FindFirst(ClaimTypes.NameIdentifier)?.Value;
}

// Register in Program.cs
builder.Services.AddSingleton<IUserIdProvider, EmailUserIdProvider>();
""", "EmailUserIdProvider.cs")}
{C(r"""
// Using Clients.User for user-targeted messages (e.g. send notification to Priya, all tabs)
await Clients.User("priya@acme.in").ReceiveMessage("System",
    "Your report is ready for download.", DateTime.UtcNow);
""", "TargetedMessage.cs")}

<h3>4. Connection mapping for direct messages</h3>
{C(r"""
// A thread-safe connection map (in-memory, single server)
public sealed class ConnectionMap
{
    private readonly ConcurrentDictionary<string, HashSet<string>> _userToConnections = new();
    private readonly object _lock = new();

    public void Add(string userId, string connectionId)
    {
        lock (_lock)
        {
            if (!_userToConnections.TryGetValue(userId, out var set))
                _userToConnections[userId] = set = new HashSet<string>();
            set.Add(connectionId);
        }
    }

    public void Remove(string userId, string connectionId)
    {
        lock (_lock)
        {
            if (_userToConnections.TryGetValue(userId, out var set))
            {
                set.Remove(connectionId);
                if (set.Count == 0) _userToConnections.TryRemove(userId, out _);
            }
        }
    }

    public IReadOnlySet<string> GetConnections(string userId) =>
        _userToConnections.TryGetValue(userId, out var set) ? set : new HashSet<string>();

    public IReadOnlyCollection<string> OnlineUsers => _userToConnections.Keys.ToList();
}
""", "ConnectionMap.cs")}
{C(r"""
// Hub using ConnectionMap for DMs
public sealed class ChatHub : Hub<IChatClient>
{
    private readonly ConnectionMap _map;
    public ChatHub(ConnectionMap map) => _map = map;

    public override Task OnConnectedAsync()
    {
        _map.Add(Context.UserIdentifier!, Context.ConnectionId);
        return base.OnConnectedAsync();
    }

    public override Task OnDisconnectedAsync(Exception? e)
    {
        _map.Remove(Context.UserIdentifier!, Context.ConnectionId);
        return base.OnDisconnectedAsync(e);
    }

    public async Task SendDirect(string targetUserId, string message)
    {
        // Clients.User uses IUserIdProvider → targets all connections for that user
        await Clients.User(targetUserId).ReceiveMessage(
            Context.UserIdentifier!, message, DateTime.UtcNow);
    }
}
""", "DmChatHub.cs")}

<h3>5. Keep-alive and timeout configuration</h3>
{C(r"""
// Server-side (Program.cs)
builder.Services.AddSignalR(opt =>
{
    opt.KeepAliveInterval        = TimeSpan.FromSeconds(15);   // server→client ping
    opt.ClientTimeoutInterval    = TimeSpan.FromSeconds(30);   // server waits this long
    opt.HandshakeTimeout         = TimeSpan.FromSeconds(15);   // initial negotiation
    opt.MaximumReceiveMessageSize = 64 * 1024;                 // 64 KB (default: 32 KB)
    opt.EnableDetailedErrors     = builder.Environment.IsDevelopment();
});
""", "SignalRConfig.cs")}
{C(r"""
// JavaScript client (index.html)
const connection = new signalR.HubConnectionBuilder()
    .withUrl("/chathub", { accessTokenFactory: () => localStorage.getItem("jwt") })
    .withAutomaticReconnect([0, 2000, 10000, 30000])  // retry after 0s, 2s, 10s, 30s
    .configureLogging(signalR.LogLevel.Information)
    .build();

connection.serverTimeoutInMilliseconds = 60000;   // must be > KeepAliveInterval * 2
connection.keepAliveIntervalInMilliseconds = 15000;
""", "chat.js", lang="javascript")}
{table(["Setting","Default","Guidance"],[
["KeepAliveInterval","15 s","Increase on slow/mobile connections"],
["ClientTimeoutInterval","30 s","≥ 2× KeepAliveInterval"],
["serverTimeoutInMilliseconds (JS)","30 s","Match server ClientTimeoutInterval"],
["withAutomaticReconnect","off","Always enable in production apps"]])}
''',
["Forgetting the <code>OnMessageReceived</code> handler; every WebSocket connection is anonymous.",
"Using the main JWT for query-string tokens in production without expiring them quickly.",
"Sending <code>HubException</code> with internal stack traces — only the message is sent, but make it safe.",
"<code>ClientTimeoutInterval</code> less than <code>KeepAliveInterval</code>; the server disconnects clients it just pinged.",
"Not registering <code>IUserIdProvider</code> when your JWT uses a non-default claim; <code>Clients.User</code> always sends to nobody."],
("40 min", [
"Add JWT auth to your Day 4 hub project. Configure the <code>OnMessageReceived</code> event. Test with a token in the query string using the Mailpit UI or a quick HTML page.",
"Implement a custom <code>IUserIdProvider</code> that uses the <code>email</code> claim. Register it and verify <code>Clients.User(email)</code> reaches only that user's connections.",
"Set <code>EnableDetailedErrors = true</code> in Development and throw a <code>HubException</code> from a hub method; observe the client receives the message."]),
[("Why can't WebSocket connections use the Authorization header?","The browser's WebSocket API does not support custom headers on the initial handshake request. The token must be in the query string or a cookie. SignalR handles reading it via the OnMessageReceived event."),
("What does IUserIdProvider do?","It maps a ClaimsPrincipal to a string user ID. SignalR uses this ID to route Clients.User(id) messages to all connections for that user. The default reads the NameIdentifier claim."),
("What is ClientTimeoutInterval?","The duration the server waits after receiving the last message (including pings) before treating the connection as dead and disconnecting. It should be at least twice the KeepAliveInterval.")],
[("Basic","Why does JWT authentication require special handling in SignalR?","WebSocket connections cannot send HTTP headers during the upgrade. The token is passed as the access_token query parameter, and the OnMessageReceived event copies it to ctx.Token before the JWT middleware validates it."),
("Basic","What is withAutomaticReconnect in the JavaScript client?","A builder option that makes the client automatically try to reconnect after a disconnect, using a configurable delay sequence. Without it, the connection is lost forever after a network blip."),
("Intermediate","How does Clients.User work internally?","SignalR maintains a mapping from user ID (from IUserIdProvider) to its current connection IDs. Clients.User looks up those IDs and sends the message to each one, handling the case where the user has multiple tabs open."),
("Intermediate","What is the difference between HubException and a regular exception in a hub method?","A HubException's message is forwarded to the client as an error response. Any other exception type causes a generic 'An unexpected error occurred' message; the actual exception is hidden to prevent information leakage."),
("Intermediate","How do you scale SignalR to multiple servers?","Use a backplane: Redis (AddStackExchangeRedis) or Azure SignalR Service (AddAzureSignalR). The backplane replicates group membership and messages across all server instances."),
("Advanced","Design a presence system for a chat app with 100 k concurrent users.","Use a Redis Sorted Set (userId → last_seen timestamp) updated on connect/ping and read by the hub. Azure SignalR Service offloads connection management. A background worker sweeps stale entries. Groups per room avoid full broadcast scanning.")])

# ================= DAY 6 — SAT =================
d6 = day(6, "SAT", "Micro-project 8: ReportMailer",
"Build a Hangfire-powered daily sales report emailer: a recurring 08:00 IST job queries sales from SQL Server via Dapper, formats an HTML email in ₹ via MailKit, includes a manual trigger endpoint, a local-only dashboard, and spins up with Docker Compose + Mailpit.",
[("ReportMailer","The micro-project: an ASP.NET Core minimal API with Hangfire recurring jobs, Dapper queries and MailKit HTML emails."),
("Dapper","A lightweight micro-ORM (Object/Relational Mapper) that extends <code>IDbConnection</code>; executes raw SQL and maps results to C# objects."),
("IST recurring job","Hangfire recurring job with <code>TimeZoneInfo.FindSystemTimeZoneById(\"India Standard Time\")</code> so it runs at 08:00 IST regardless of server timezone."),
("LocalRequestsOnlyAuthorizationFilter","Hangfire built-in filter that restricts the dashboard to <code>127.0.0.1</code>; suitable for development and internal tools.")],
["Dapper is <b>not</b> available in the sandbox — the code is written correctly against the real API and shown as expected output.",
"SQL Server 2022 Developer in Docker is the assumed setup.",
"The manual trigger endpoint (<code>POST /reports/trigger</code>) calls the same job method directly — no special Hangfire code needed.",
"Use Mailpit on port 1025/8025 for local testing; switch to a real SMTP relay (SES, SendGrid) in production via appsettings overrides."],
f'''
<h3>Project scaffold</h3>
{C(r"""
mkdir ReportMailer && cd ReportMailer
dotnet new webapi -n ReportMailer --no-openapi
cd ReportMailer
dotnet add package Hangfire.AspNetCore --version 1.8.*
dotnet add package Hangfire.SqlServer --version 1.8.*
dotnet add package Dapper --version 2.1.*
dotnet add package Microsoft.Data.SqlClient --version 5.2.*
dotnet add package MailKit --version 4.7.*
""", "scaffold.sh", lang="bash")}

<h3>Folder layout</h3>
{C(r"""
ReportMailer/
├── Program.cs
├── appsettings.json
├── appsettings.Development.json
├── docker-compose.yml
├── Jobs/
│   └── DailySalesReportJob.cs
├── Services/
│   ├── IEmailSender.cs
│   └── MailKitEmailSender.cs
├── Options/
│   └── EmailOptions.cs
├── Data/
│   └── SalesQuery.cs
└── Templates/
    └── SalesReportTemplate.cs
""", "layout.txt", lang="text")}

<h3>docker-compose.yml</h3>
{C(r"""
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      ACCEPT_EULA: "Y"
      SA_PASSWORD: "YourStrong@Pass123"
    ports:
      - "1433:1433"

  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI
""", "docker-compose.yml", lang="yaml")}
{C(r"""
docker compose up -d
# Wait ~20 s for SQL Server to initialise
""", "run.sh", lang="bash")}

<h3>Database schema setup</h3>
{C(r"""
-- Run once to set up the database
CREATE DATABASE SalesDb;
GO
USE SalesDb;
GO

CREATE TABLE Orders (
    Id          INT           IDENTITY(1,1) PRIMARY KEY,
    OrderDate   DATE          NOT NULL,
    CustomerName NVARCHAR(100) NOT NULL,
    CityName    NVARCHAR(60)  NOT NULL,
    TotalAmount DECIMAL(12,2) NOT NULL
);
GO

INSERT INTO Orders (OrderDate, CustomerName, CityName, TotalAmount) VALUES
  ('2026-11-14', 'Ravi Sharma',   'Mumbai',    14750.00),
  ('2026-11-14', 'Priya Nair',    'Bengaluru', 8200.00),
  ('2026-11-14', 'Amit Verma',    'Delhi',     22500.00),
  ('2026-11-13', 'Meena Reddy',   'Hyderabad', 5900.00);
GO
""", "setup.sql", lang="sql")}

<h3>SalesQuery.cs — Dapper data access</h3>
{C(r"""
using Dapper;
using Microsoft.Data.SqlClient;

namespace ReportMailer.Data;

public sealed record SaleRow(string City, int Orders, decimal Total);

public sealed class SalesQuery(string connString)
{
    public async Task<IReadOnlyList<SaleRow>> GetDailySummaryAsync(DateOnly date,
        CancellationToken ct = default)
    {
        await using var conn = new SqlConnection(connString);
        const string sql =
            "SELECT CityName AS City, COUNT(*) AS Orders, SUM(TotalAmount) AS Total " +
            "FROM Orders WHERE OrderDate = @Date " +
            "GROUP BY CityName ORDER BY Total DESC;";

        var rows = await conn.QueryAsync<SaleRow>(
            new CommandDefinition(sql, new { Date = date.ToDateTime(TimeOnly.MinValue) },
                cancellationToken: ct));
        return rows.ToList();
    }
}
""", "Data/SalesQuery.cs")}

<h3>SalesReportTemplate.cs — HTML email</h3>
{C(r"""
namespace ReportMailer.Templates;

public static class SalesReportTemplate
{
    public static string Build(DateOnly date, IReadOnlyList<Data.SaleRow> rows)
    {
        decimal grandTotal = rows.Sum(r => r.Total);
        int totalOrders    = rows.Sum(r => r.Orders);

        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < rows.Count; i++)
        {
            var r = rows[i];
            string bg = i % 2 == 0 ? "#ffffff" : "#f7f9fc";
            sb.AppendLine($"<tr style=\"background:{bg}\">");
            sb.AppendLine($"  <td style=\"padding:8px 12px\">{r.City}</td>");
            sb.AppendLine($"  <td style=\"padding:8px 12px;text-align:right\">{r.Orders}</td>");
            sb.AppendLine($"  <td style=\"padding:8px 12px;text-align:right\">&#8377;{r.Total:N2}</td>");
            sb.AppendLine("</tr>");
        }
        string rowHtml = sb.ToString();

        return $"<!DOCTYPE html><html><body style=\"font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#222\">" +
               $"<div style=\"background:#1a3c6e;padding:20px;border-radius:4px 4px 0 0\">" +
               $"<h1 style=\"color:#fff;margin:0;font-size:20px\">Daily Sales Report</h1>" +
               $"<p style=\"color:#a8c0e0;margin:4px 0 0\">Date: {date:dd MMMM yyyy}</p></div>" +
               "<div style=\"padding:20px;border:1px solid #dde3ec;border-top:none\">" +
               "<table style=\"width:100%;border-collapse:collapse\"><thead>" +
               "<tr style=\"background:#1a3c6e;color:#fff\">" +
               "<th style=\"padding:10px 12px;text-align:left\">City</th>" +
               "<th style=\"padding:10px 12px;text-align:right\">Orders</th>" +
               "<th style=\"padding:10px 12px;text-align:right\">Revenue</th>" +
               $"</tr></thead><tbody>{rowHtml}</tbody><tfoot>" +
               "<tr style=\"font-weight:bold;background:#e8edf5\">" +
               "<td style=\"padding:10px 12px\">Grand Total</td>" +
               $"<td style=\"padding:10px 12px;text-align:right\">{totalOrders}</td>" +
               $"<td style=\"padding:10px 12px;text-align:right\">&#8377;{grandTotal:N2}</td>" +
               "</tr></tfoot></table></div>" +
               "<p style=\"color:#999;font-size:11px;padding:8px 20px\">Auto-generated by Acme Sales System</p>" +
               "</body></html>";
    }
}
""", "Templates/SalesReportTemplate.cs")}

<h3>DailySalesReportJob.cs</h3>
{C(r"""
using Hangfire;
using ReportMailer.Data;
using ReportMailer.Services;
using ReportMailer.Templates;

namespace ReportMailer.Jobs;

public sealed class DailySalesReportJob(
    SalesQuery query,
    IEmailSender mailer,
    IConfiguration config,
    ILogger<DailySalesReportJob> log)
{
    [AutomaticRetry(Attempts = 3)]
    public async Task RunAsync(CancellationToken ct = default)
    {
        var date = DateOnly.FromDateTime(DateTime.Today);
        log.LogInformation("Running daily sales report for {Date}", date);

        var rows = await query.GetDailySummaryAsync(date, ct);

        if (rows.Count == 0)
        {
            log.LogWarning("No sales data for {Date} — skipping email", date);
            return;
        }

        string html = SalesReportTemplate.Build(date, rows);
        string to   = config["ReportEmail:To"] ?? "cfo@acme.in";

        await mailer.SendAsync(
            to, "CFO",
            subject: $"Daily Sales Report — {date:dd MMM yyyy}",
            htmlBody: html,
            textBody: $"Sales report for {date:dd MMM yyyy}. Total: Rs. {rows.Sum(r => r.Total):N2}",
            ct);

        log.LogInformation("Sales report emailed to {To}", to);
    }
}
""", "Jobs/DailySalesReportJob.cs")}

<h3>Program.cs</h3>
{C(r"""
using Hangfire;
using Hangfire.Dashboard;
using Hangfire.SqlServer;
using ReportMailer.Data;
using ReportMailer.Jobs;
using ReportMailer.Options;
using ReportMailer.Services;

var builder = WebApplication.CreateBuilder(args);

var connStr = builder.Configuration.GetConnectionString("SalesDb")!;

// Hangfire
builder.Services.AddHangfire(cfg => cfg
    .SetDataCompatibilityLevel(CompatibilityLevel.Version_180)
    .UseSimpleAssemblyNameTypeSerializer()
    .UseRecommendedSerializerSettings()
    .UseSqlServerStorage(builder.Configuration.GetConnectionString("HangfireDb")));
builder.Services.AddHangfireServer();

// Email
builder.Services.Configure<EmailOptions>(builder.Configuration.GetSection(EmailOptions.Section));
builder.Services.AddSingleton<IEmailSender, MailKitEmailSender>();

// Data
builder.Services.AddSingleton(new SalesQuery(connStr));

// Job (transient so Hangfire resolves a new instance per execution)
builder.Services.AddTransient<DailySalesReportJob>();

var app = builder.Build();

// Dashboard — local requests only
app.UseHangfireDashboard("/hangfire", new DashboardOptions
{
    Authorization = new[] { new LocalRequestsOnlyAuthorizationFilter() }
});

// Register recurring job at 08:00 IST every day
var ist = TimeZoneInfo.FindSystemTimeZoneById("India Standard Time");
RecurringJob.AddOrUpdate<DailySalesReportJob>(
    "daily-sales-report",
    job => job.RunAsync(CancellationToken.None),
    Cron.Daily(hour: 8, minute: 0),
    new RecurringJobOptions { TimeZone = ist });

// Manual trigger (useful for demos and ops)
app.MapPost("/reports/trigger", async (DailySalesReportJob job) =>
{
    await job.RunAsync();
    return Results.Ok(new { triggered = true, at = DateTime.UtcNow });
})
.WithName("TriggerReport");

app.MapGet("/health", () => Results.Ok("healthy"));

app.Run();
""", "Program.cs")}

<h3>appsettings.json</h3>
{C(r"""
{
  "ConnectionStrings": {
    "SalesDb":    "Server=localhost,1433;Database=SalesDb;User Id=sa;Password=YourStrong@Pass123;TrustServerCertificate=true",
    "HangfireDb": "Server=localhost,1433;Database=SalesHangfire;User Id=sa;Password=YourStrong@Pass123;TrustServerCertificate=true"
  },
  "Email": {
    "Host":     "localhost",
    "Port":     1025,
    "UseSsl":   false,
    "From":     "noreply@acme.in",
    "FromName": "Acme Sales"
  },
  "ReportEmail": {
    "To": "cfo@acme.in"
  }
}
""", "appsettings.json", lang="json")}

<h3>How to run and expected output</h3>
{C(r"""
# 1. Start Docker services
docker compose up -d

# 2. Wait for SQL Server, then create schema
sqlcmd -S localhost,1433 -U sa -P 'YourStrong@Pass123' -i setup.sql

# 3. Run the app
dotnet run

# 4. Manually trigger the report
curl -X POST http://localhost:5000/reports/trigger
# → {"triggered":true,"at":"2026-11-14T..."}

# 5. Check Mailpit for the email
open http://localhost:8025

# 6. Check Hangfire dashboard (local only)
open http://localhost:5000/hangfire
""", "run.sh", lang="bash")}
{C(r"""
// Console log output
info: ReportMailer.Jobs.DailySalesReportJob[0]
      Running daily sales report for 2026-11-14
info: ReportMailer.Services.MailKitEmailSender[0]
      Email sent to {To} subject Daily Sales Report — 14 Nov 2026
info: ReportMailer.Jobs.DailySalesReportJob[0]
      Sales report emailed to cfo@acme.in
""", "expected-console.txt", lang="text")}

<h3>Stretch goals</h3>
{ul(["Add a weekly summary job (Mondays at 09:00 IST) using <code>Cron.Weekly(DayOfWeek.Monday, 9)</code>.",
"Parameterise the report date in the trigger endpoint: <code>POST /reports/trigger?date=2026-11-13</code>.",
"Add city-level totals to the email, with a bar chart using inline SVG.",
"Add an <code>[Authorize(Roles=\"Admin\")]</code> filter on the trigger endpoint (from Week 20 auth service).",
"Switch from Mailpit to real SES by changing <code>appsettings.Production.json</code> only."])}
''',
iqs=[("Basic","What NuGet packages does this project need?","Hangfire.AspNetCore and Hangfire.SqlServer (job scheduling), Dapper and Microsoft.Data.SqlClient (database), MailKit (email)."),
("Basic","How do you trigger a Hangfire recurring job manually?","Either call RecurringJob.TriggerJob(\"job-id\") or, as done here, resolve the job class from DI and call its method directly — no Hangfire-specific API needed."),
("Intermediate","Why is DailySalesReportJob registered as Transient?","Hangfire resolves a new instance per execution via the DI container. If it were Singleton it would hold on to disposable services. Transient ensures a fresh instance and correct lifetime management."),
("Intermediate","How do you make the Hangfire dashboard available internally but not to the public?","Use LocalRequestsOnlyAuthorizationFilter to allow only 127.0.0.1, or write a custom IDashboardAuthorizationFilter that checks the authenticated user's role.")])

# ================= DAY 7 — SUN =================
d7 = day(7, "SUN", "Micro-project 9: ChatApi + Week Review",
"Build a JWT-authenticated SignalR chat API with rooms, DMs, typing indicators, EF Core message persistence and an HTML/JS test client. Then break it, write the README, commit, and quiz yourself on the week.",
[("ChatApi","The micro-project: SignalR hub with JWT auth, groups (rooms), DMs, typing, EF Core last-50 persistence, online-user tracking, minimal HTML/JS client."),
("Room persistence","On JoinRoom, query the last 50 messages for that room from SQL Server via EF Core and push them to the joining client."),
("Online-user tracker","A singleton <code>ConnectionMap</code> that maps user IDs to their active connection IDs; exposed via a <code>GET /users/online</code> endpoint.")],
["The HTML/JS test client uses <code>@microsoft/signalr</code> from the jsDelivr CDN — no npm required.",
"Keep the EF Core context access inside <code>IServiceScopeFactory</code> in the hub (hubs are transient, DbContext is scoped, so create a scope per hub method that needs it).",
"The online-user tracker is in-memory; for multi-server you would replace it with a Redis set."],
f'''
<h3>Scaffold</h3>
{C(r"""
mkdir ChatApi && cd ChatApi
dotnet new webapi -n ChatApi --no-openapi
cd ChatApi
dotnet add package Microsoft.EntityFrameworkCore.SqlServer --version 8.*
dotnet add package Microsoft.EntityFrameworkCore.Tools     --version 8.*
dotnet add package Microsoft.AspNetCore.Authentication.JwtBearer --version 8.*
""", "scaffold.sh", lang="bash")}

<h3>Folder layout</h3>
{C(r"""
ChatApi/
├── Program.cs
├── appsettings.json
├── docker-compose.yml
├── Hubs/
│   └── ChatHub.cs
├── Data/
│   ├── ChatDbContext.cs
│   └── ChatMessage.cs
├── Services/
│   ├── ConnectionMap.cs
│   └── IUserIdProvider.cs
└── wwwroot/
    └── index.html          ← HTML/JS test client
""", "layout.txt", lang="text")}

<h3>ChatMessage.cs and ChatDbContext.cs</h3>
{C(r"""
// Data/ChatMessage.cs
public sealed class ChatMessage
{
    public int    Id        { get; set; }
    public string Room      { get; set; } = "";
    public string SenderId  { get; set; } = "";
    public string SenderName{ get; set; } = "";
    public string Body      { get; set; } = "";
    public DateTime SentAt  { get; set; }
}
""", "Data/ChatMessage.cs")}
{C(r"""
// Data/ChatDbContext.cs
using Microsoft.EntityFrameworkCore;

public sealed class ChatDbContext : DbContext
{
    public ChatDbContext(DbContextOptions<ChatDbContext> opt) : base(opt) { }
    public DbSet<ChatMessage> Messages => Set<ChatMessage>();

    protected override void OnModelCreating(ModelBuilder mb)
    {
        mb.Entity<ChatMessage>(e =>
        {
            e.HasIndex(m => new { m.Room, m.SentAt });  // fast last-50 query
        });
    }
}
""", "Data/ChatDbContext.cs")}

<h3>ChatHub.cs</h3>
{C(r"""
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.SignalR;

[Authorize]
public sealed class ChatHub : Hub<IChatClient>
{
    private readonly ConnectionMap _map;
    private readonly IServiceScopeFactory _scopes;
    private readonly ILogger<ChatHub> _log;

    public ChatHub(ConnectionMap map, IServiceScopeFactory scopes, ILogger<ChatHub> log)
        => (_map, _scopes, _log) = (map, scopes, log);

    // ── Connection lifecycle ──────────────────────────────────────────────
    public override async Task OnConnectedAsync()
    {
        _map.Add(Context.UserIdentifier!, Context.ConnectionId);
        await Clients.Others.UserOnline(Context.UserIdentifier!);
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? e)
    {
        _map.Remove(Context.UserIdentifier!, Context.ConnectionId);
        await Clients.Others.UserOffline(Context.UserIdentifier!);
        await base.OnDisconnectedAsync(e);
    }

    // ── Rooms ─────────────────────────────────────────────────────────────
    public async Task JoinRoom(string room)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, room);

        // Load last 50 messages for this room from DB
        await using var scope = _scopes.CreateAsyncScope();
        var db = scope.ServiceProvider.GetRequiredService<ChatDbContext>();
        var history = await db.Messages
            .Where(m => m.Room == room)
            .OrderByDescending(m => m.SentAt)
            .Take(50)
            .OrderBy(m => m.SentAt)
            .Select(m => new MessageDto(m.SenderId, m.SenderName, m.Body, m.SentAt))
            .ToListAsync();

        await Clients.Caller.RoomHistory(room, history);
        await Clients.OthersInGroup(room).UserJoinedRoom(Context.UserIdentifier!, room);
    }

    public async Task LeaveRoom(string room)
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, room);
        await Clients.Group(room).UserLeftRoom(Context.UserIdentifier!, room);
    }

    // ── Messages ──────────────────────────────────────────────────────────
    public async Task SendToRoom(string room, string body)
    {
        var msg = new ChatMessage
        {
            Room       = room,
            SenderId   = Context.UserIdentifier!,
            SenderName = Context.User!.Identity!.Name!,
            Body       = body,
            SentAt     = DateTime.UtcNow
        };

        await using var scope = _scopes.CreateAsyncScope();
        var db = scope.ServiceProvider.GetRequiredService<ChatDbContext>();
        db.Messages.Add(msg);
        await db.SaveChangesAsync();

        await Clients.Group(room).ReceiveMessage(
            new MessageDto(msg.SenderId, msg.SenderName, body, msg.SentAt));
    }

    public async Task SendDirect(string targetUserId, string body)
    {
        // Clients.User uses IUserIdProvider → all tabs of that user
        await Clients.User(targetUserId).ReceiveDm(
            Context.UserIdentifier!, Context.User!.Identity!.Name!, body, DateTime.UtcNow);
    }

    public async Task Typing(string room) =>
        await Clients.OthersInGroup(room).UserTyping(Context.UserIdentifier!);
}

// Client-side method contract
public interface IChatClient
{
    Task ReceiveMessage(MessageDto msg);
    Task ReceiveDm(string fromId, string fromName, string body, DateTime at);
    Task RoomHistory(string room, List<MessageDto> history);
    Task UserJoinedRoom(string userId, string room);
    Task UserLeftRoom(string userId, string room);
    Task UserTyping(string userId);
    Task UserOnline(string userId);
    Task UserOffline(string userId);
}

public sealed record MessageDto(string SenderId, string SenderName, string Body, DateTime SentAt);
""", "Hubs/ChatHub.cs")}

<h3>Program.cs</h3>
{C(r"""
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.Text;

var builder = WebApplication.CreateBuilder(args);

// EF Core
builder.Services.AddDbContext<ChatDbContext>(opt =>
    opt.UseSqlServer(builder.Configuration.GetConnectionString("ChatDb")));

// JWT
var jwtKey = builder.Configuration["Jwt:Key"]!;
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(opt =>
    {
        opt.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer           = false,
            ValidateAudience         = false,
            ValidateLifetime         = true,
            ValidateIssuerSigningKey = true,
            IssuerSigningKey         = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
        };
        opt.Events = new JwtBearerEvents
        {
            OnMessageReceived = ctx =>
            {
                var token = ctx.Request.Query["access_token"];
                if (!string.IsNullOrEmpty(token) && ctx.Request.Path.StartsWithSegments("/chathub"))
                    ctx.Token = token;
                return Task.CompletedTask;
            }
        };
    });
builder.Services.AddAuthorization();

// SignalR
builder.Services.AddSignalR();
builder.Services.AddSingleton<ConnectionMap>();

// Serve wwwroot (test client)
builder.Services.AddSpaStaticFiles(cfg => cfg.RootPath = "wwwroot");

var app = builder.Build();

// Apply migrations on startup (dev convenience)
using (var scope = app.Services.CreateScope())
    scope.ServiceProvider.GetRequiredService<ChatDbContext>().Database.Migrate();

app.UseAuthentication();
app.UseAuthorization();
app.UseStaticFiles();

// Issue a test JWT (dev only — remove in production)
app.MapGet("/dev/token", (string name, string sub) =>
{
    var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey));
    var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
    var claims = new[] { new System.Security.Claims.Claim("sub", sub),
                          new System.Security.Claims.Claim("name", name) };
    var token = new System.IdentityModel.Tokens.Jwt.JwtSecurityToken(
        claims: claims, expires: DateTime.UtcNow.AddHours(8), signingCredentials: creds);
    return Results.Ok(new { token = new System.IdentityModel.Tokens.Jwt.JwtSecurityTokenHandler().WriteToken(token) });
});

app.MapGet("/users/online", (ConnectionMap map) => Results.Ok(map.OnlineUsers));
app.MapHub<ChatHub>("/chathub");

app.Run();
""", "Program.cs")}

<h3>HTML/JS test client (wwwroot/index.html)</h3>
{C(r"""
<!DOCTYPE html>
<html>
<head>
  <title>ChatApi Test Client</title>
  <script src="https://cdn.jsdelivr.net/npm/@microsoft/signalr@8.0.7/dist/browser/signalr.min.js"></script>
  <style>
    body{font-family:Arial,sans-serif;max-width:700px;margin:20px auto}
    #log{border:1px solid #ccc;height:300px;overflow-y:auto;padding:8px;font-size:13px}
    .dm{color:#0057b8} .sys{color:#888;font-style:italic}
    input,button{margin:4px;padding:6px 10px}
  </style>
</head>
<body>
<h2>ChatApi Test Client</h2>
<div>
  Token: <input id="token" size="60" placeholder="paste JWT here">
  <button onclick="connect()">Connect</button>
  <span id="status" style="color:red">Disconnected</span>
</div>
<div>
  Room: <input id="room" value="general">
  <button onclick="join()">Join</button>
  <button onclick="leave()">Leave</button>
</div>
<div>
  Msg: <input id="msg" size="40">
  <button onclick="send()">Send to Room</button>
</div>
<div>
  DM to userId: <input id="dmTo" size="20">
  <input id="dmMsg" size="30">
  <button onclick="sendDm()">Send DM</button>
</div>
<div id="log"></div>

<script>
let conn;
function log(text, cls='') {
  const d = document.getElementById('log');
  d.innerHTML += '<div class="' + cls + '">' + new Date().toLocaleTimeString() + ' ' + text + '</div>';
  d.scrollTop = d.scrollHeight;
}
function connect() {
  const jwt = document.getElementById('token').value.trim();
  conn = new signalR.HubConnectionBuilder()
    .withUrl('/chathub', { accessTokenFactory: () => jwt })
    .withAutomaticReconnect()
    .build();
  conn.on('ReceiveMessage', m => log('[' + m.senderName + '] ' + m.body));
  conn.on('ReceiveDm',      (from,name,body) => log('DM from ' + name + ': ' + body, 'dm'));
  conn.on('RoomHistory',    (room,hist) => hist.forEach(m => log('[hist][' + m.senderName + '] ' + m.body,'sys')));
  conn.on('UserJoinedRoom', (u,r) => log(u + ' joined ' + r, 'sys'));
  conn.on('UserLeftRoom',   (u,r) => log(u + ' left ' + r, 'sys'));
  conn.on('UserTyping',     u     => log(u + ' is typing…', 'sys'));
  conn.on('UserOnline',     u     => log(u + ' online', 'sys'));
  conn.on('UserOffline',    u     => log(u + ' offline', 'sys'));
  conn.start()
    .then(() => { document.getElementById('status').textContent='Connected'; document.getElementById('status').style.color='green'; })
    .catch(e => log('Connect error: ' + e, 'sys'));
}
function join()   { conn.invoke('JoinRoom',  document.getElementById('room').value); }
function leave()  { conn.invoke('LeaveRoom', document.getElementById('room').value); }
function send()   {
  const r = document.getElementById('room').value, m = document.getElementById('msg').value;
  conn.invoke('SendToRoom', r, m);
  conn.invoke('Typing', r);
}
function sendDm() {
  conn.invoke('SendDirect', document.getElementById('dmTo').value, document.getElementById('dmMsg').value);
}
</script>
</body>
</html>
""", "wwwroot/index.html", lang="html")}

<h3>Try-to-break table</h3>
{table(["Scenario","Expected behaviour"],[
["Connect without a JWT","Connection refused (401)"],
["Use an expired JWT","Connection refused (401)"],
["Send to a room you haven't joined","Message not received by room members (not in the SignalR group)"],
["Two browser tabs, same JWT, same user","Both receive DMs; Clients.User delivers to both connections"],
["Send a 100 KB message","Rejected by server (MaximumReceiveMessageSize = 32 KB default); raise or handle on client"],
["Disconnect abruptly (kill tab)","OnDisconnectedAsync fires; user removed from ConnectionMap; group members see UserOffline"],
["Send a message with HTML <script>","Stored and echoed as plain text; JS client must HTML-escape before inserting into DOM"],
["JoinRoom when history is empty","RoomHistory fires with an empty list; client shows no history"],
["Send 50 messages rapidly","All 50 persisted; last 50 on next JoinRoom shows newest 50"],
["Restart server","JWT still valid; client reconnects via withAutomaticReconnect; groups are re-joined on JoinRoom"]])}

<h3>README.md template</h3>
{C(r"""
# ChatApi — Week 21 Micro-project

Real-time chat API built with ASP.NET Core 8, SignalR, EF Core and JWT auth.

## Features
- JWT-authenticated WebSocket connections (Bearer token via ?access_token=)
- Rooms: join, leave, receive last 50 messages on join
- DMs: targeted to all connections for a user
- Typing indicators
- Online user tracking
- EF Core + SQL Server message persistence

## Quick start
```bash
docker compose up -d
dotnet ef database update
dotnet run
# Get a test token
curl "http://localhost:5000/dev/token?name=Priya&sub=priya@acme.in"
# Open test client
open http://localhost:5000
```

## Architecture
- `Hubs/ChatHub.cs` — SignalR hub (rooms, DMs, typing)
- `Services/ConnectionMap.cs` — in-memory online user registry
- `Data/ChatDbContext.cs` — EF Core context, ChatMessage entity

## Stretch goals
- [ ] Add Redis backplane for multi-server deployment
- [ ] Store unread DM counts; deliver missed messages on reconnect
- [ ] Add read receipts (Clients.User to sender after target reads)
""", "README.md", lang="text")}

<h3>Git commands</h3>
{C(r"""
cd ChatApi
git init
git add .
git commit -m "Week 21: ChatApi — SignalR JWT auth, rooms, DMs, EF Core persistence"
git remote add origin https://github.com/nayak22/dotnet-week21-chatapi.git
git push -u origin main
""", "git.sh", lang="bash")}

<h3>Week 21 checklist</h3>
{ul([
"IHostedService vs BackgroundService — know when to use each",
"PeriodicTimer — skips ticks, pairs with CancellationToken",
"IServiceScopeFactory in a singleton worker",
"Never-die error handling pattern in ExecuteAsync",
"System.Threading.Channels — bounded vs unbounded, back-pressure, ReadAllAsync",
"Hangfire: install, SQL Server storage, fire-and-forget, delayed, recurring, continuation",
"Hangfire: dashboard auth, [AutomaticRetry], idempotency pattern",
"MailKit over System.Net.Mail — why, BodyBuilder, multipart/alternative",
"IEmailSender interface and EmailOptions with user-secrets",
"Mailpit / smtp4dev for local SMTP testing",
"SignalR: Hub vs Hub&lt;T&gt;, Clients.All/Caller/Group/User/Others",
"Hub lifetime per invocation, state in singleton, IHubContext",
"OnConnectedAsync / OnDisconnectedAsync, group management",
"JWT OnMessageReceived event for WebSocket auth",
"[Authorize] on hubs, IUserIdProvider, Clients.User",
"KeepAliveInterval, ClientTimeoutInterval, withAutomaticReconnect",
"ReportMailer: Hangfire + Dapper + MailKit + Mailpit",
"ChatApi: JWT hub, rooms, DMs, typing, EF Core persistence, HTML/JS client"
])}

<h3>Quiz — predict the output / does it compile?</h3>
<details><summary>Q1. What is logged when the app starts with this worker, before any HTTP request arrives?</summary>
{C(r"""
public class MyWorker : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        Console.WriteLine("A");
        await Task.Yield();
        Console.WriteLine("B");
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1));
        await timer.WaitForNextTickAsync(ct);
        Console.WriteLine("C");
    }
}
""")}
<b>"A" then "B" then (after ~1 s) "C".</b> <code>await Task.Yield()</code> gives the host a chance to finish starting, but then execution continues on the thread-pool. "A" is logged before the yield, "B" after, then the timer fires.</details>

<details><summary>Q2. Does this compile? If so, what does it do?</summary>
{C(r"""
public interface IOrderClient { Task ReceiveOrder(string sku, int qty); }
public class OrderHub : Hub<IOrderClient>
{
    public Task Push(string sku, int qty) =>
        Clients.All.ReceiveOder(sku, qty);  // note: "Oder"
}
""")}
<b>No, compile error.</b> <code>IOrderClient</code> has no method <code>ReceiveOder</code>. This is exactly the advantage of <code>Hub&lt;T&gt;</code> — typos become build failures.</details>

<details><summary>Q3. What happens when this Hangfire job throws an exception?</summary>
{C(r"""
[AutomaticRetry(Attempts = 2)]
public Task ProcessPayment(int orderId)
{
    throw new InvalidOperationException("gateway down");
}
""")}
<b>Hangfire retries 2 more times (3 attempts total) with exponential back-off.</b> After the third failure the job moves to the Failed state. It stays in SQL Server and can be manually re-queued from the dashboard.</details>

<details><summary>Q4. Why does Clients.User("priya@acme.in") send to nobody?</summary>
{C(r"""
// IUserIdProvider not registered; default NameIdentifier claim used.
// JWT contains: { "sub": "priya@acme.in", "name": "Priya" }
// No "nameidentifier" or "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier" claim.
await Clients.User("priya@acme.in").ReceiveMessage("bot", "hi", DateTime.UtcNow);
""")}
<b>The default IUserIdProvider reads the NameIdentifier claim.</b> The JWT uses "sub", which maps to <code>ClaimTypes.NameIdentifier</code> in Microsoft's JWT handler — so it should work if the JWT is issued correctly. If it doesn't, register a custom <code>IUserIdProvider</code> that reads <code>sub</code> explicitly.</details>

<details><summary>Q5. What is the output? Does it compile?</summary>
{C(r"""
var ch = Channel.CreateBounded<int>(2);
await ch.Writer.WriteAsync(1);
await ch.Writer.WriteAsync(2);
// does NOT await a third write
ch.Writer.TryWrite(3, out _);  // wrong overload
Console.WriteLine(await ch.Reader.ReadAsync());
""")}
<b>Does not compile.</b> <code>TryWrite</code> takes a single argument (the item) and returns bool. The correct call is <code>ch.Writer.TryWrite(3)</code>. The overload <code>TryWrite(T, out T)</code> does not exist. After fixing, output would be <b>1</b> (the first item).</details>

{tip("Next week: <b>Week 22 — Phase 2 exit check.</b> You will review everything from Week 11 to 21 — SQL Server, EF Core, ASP.NET Core, auth, background jobs and SignalR — with a comprehensive quiz, mock API design interview and an integration project tying all the pieces together.")}
''',
iqs=[("Basic","What is the access_token query parameter used for in SignalR?","WebSocket and SSE connections cannot send custom HTTP headers during the handshake. The JWT is passed as ?access_token= in the URL and read by the OnMessageReceived JWT Bearer event handler before the middleware validates it."),
("Intermediate","How does EF Core message persistence work in the ChatHub without injecting DbContext directly?","Hubs are transient; DbContext is scoped. Injecting DbContext directly would cause a lifetime mismatch error. Instead, inject IServiceScopeFactory and create an async scope (CreateAsyncScope) per hub method that needs the database."),
("Intermediate","How does withAutomaticReconnect work and what should the server do when a client reconnects?","The JS client retries the connection using the configured delays (e.g. 0s, 2s, 10s, 30s). On reconnect Context.ConnectionId is new; the hub's OnConnectedAsync fires again and the client must re-join rooms. The server cannot distinguish reconnect from a fresh connect at the hub level."),
("Intermediate","How would you prevent SQL injection in the Dapper query used in ReportMailer?","Dapper uses parameterised queries: parameters are passed as an anonymous object (new { Date = date }) and translated to SQL parameters by the driver, never string-concatenated. This is the same protection as EF Core.")])

# ================= BUILD =================
days = "\n".join([d1, d2, d3, d4, d5, d6, d7])

cards = [
    (1, "MON", "Background Services and Channels", "BackgroundService", "IHostedService, PeriodicTimer, IServiceScopeFactory in workers, never-die error handling, Channels.", "2 hrs"),
    (2, "TUE", "Hangfire: Reliable Background Jobs", "Hangfire", "SQL Server storage, fire-and-forget, delayed, recurring (IST cron), continuations, dashboard security.", "2 hrs"),
    (3, "WED", "Sending Email with MailKit", "MailKit", "MimeMessage, BodyBuilder, IEmailSender, options + user-secrets, Mailpit in Docker.", "2 hrs"),
    (4, "THU", "SignalR Hubs", "SignalR Hubs", "Hub&lt;T&gt;, Clients.All/Caller/Group/User, connection events, groups, IHubContext from background services.", "2 hrs"),
    (5, "FRI", "SignalR Auth &amp; Advanced", "SignalR Auth", "JWT OnMessageReceived, [Authorize] hubs, IUserIdProvider, DMs, keep-alive, reconnect.", "2 hrs"),
    (6, "SAT", "Micro-project 8: ReportMailer", "Project: ReportMailer", "Hangfire recurring job (08:00 IST), Dapper sales query, MailKit HTML email, Mailpit, dashboard.", "4 hrs"),
    (7, "SUN", "Micro-project 9: ChatApi + Review", "Project: ChatApi", "JWT SignalR chat, rooms, DMs, typing, EF Core persistence, HTML/JS client, quiz, checklist.", "4 hrs"),
]

build(
    "/home/claude/build/week04.html",
    "/home/claude/build/week21.html",
    21,
    "Week 21 — Background Jobs and Real-time with SignalR",
    "Phase 2",
    "~18 hrs",
    ["Phase 2 · Week 21 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "Jobs + chat"],
    "Long-running work and real-time messaging are two pillars of production .NET apps. This week you will implement background workers and periodic jobs with <code>IHostedService</code> and <code>BackgroundService</code>, manage durable job queues with Hangfire, send HTML email via MailKit, and build authenticated real-time chat with SignalR — finishing with two micro-projects: a daily sales-report emailer and a JWT-protected chat API.",
    cards,
    days
)
print("built week21")
