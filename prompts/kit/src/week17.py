import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Program.cs, Kestrel and the Middleware Pipeline",
"Understand what Program.cs does, how Kestrel serves HTTP, what the middleware pipeline is, and write both inline and class-based middleware that runs in the correct order.",
[("Kestrel","The cross-platform HTTP server embedded in every ASP.NET Core app. It listens on TCP ports and translates bytes into <code>HttpContext</code>."),
("Minimal hosting model","The <code>WebApplication.CreateBuilder</code> + <code>app.Run()</code> pattern introduced in .NET 6 that removes Startup.cs."),
("WebApplicationBuilder","Returned by <code>WebApplication.CreateBuilder()</code>. Exposes <code>Services</code> (DI) and <code>Configuration</code>."),
("WebApplication","The built app. Exposes <code>Use*</code> methods to register middleware, then <code>Run()</code>."),
("Middleware","A component that handles an HTTP request and optionally calls the next component."),
("RequestDelegate","<code>Func&lt;HttpContext, Task&gt;</code> — the signature every middleware ultimately is."),
("HttpContext","One instance per request, holding <code>Request</code>, <code>Response</code>, <code>User</code>, <code>Items</code>, etc."),
("Pipeline","The ordered chain of middleware components. The first registered runs first on the way in and last on the way out."),
("Use","Adds middleware and calls <code>next()</code> — both before and after the next component run."),
("Run","Adds a terminal middleware; never calls <code>next()</code>."),
("Map","Branches the pipeline based on a URL path prefix."),
("launchSettings.json","VS/VS Code config for launch profiles — sets ports, environment, env vars. Not deployed."),
("ASPNETCORE_ENVIRONMENT","Env var that sets the environment name (<code>Development</code> / <code>Staging</code> / <code>Production</code>).")],
["Middleware order matters: auth must come before authorisation, routing before endpoints.",
"<code>Use</code> without calling <code>next()</code> is effectively a <code>Run</code> — it short-circuits.",
"Kestrel is production-ready but can be fronted by Nginx/IIS for TLS termination.",
"<code>app.Environment.IsDevelopment()</code> is the idiomatic guard for dev-only middleware.",
"<code>WebApplication.CreateBuilder</code> already registers logging, configuration and DI."],
f'''
<h3>1. Program.cs anatomy</h3>
{C(r"""
// Program.cs — every line has a job
var builder = WebApplication.CreateBuilder(args);  // ① wire up config, DI, logging

builder.Services.AddControllers();                 // ② register services (later days)

var app = builder.Build();                         // ③ build — no more service registration after this

// ④ — MIDDLEWARE PIPELINE (order matters!)
app.UseHttpsRedirection();                         // redirect HTTP → HTTPS
app.UseRouting();                                  // match URL to an endpoint
app.UseAuthentication();                           // who are you?
app.UseAuthorization();                            // are you allowed?
app.MapControllers();                              // wire controller actions as endpoints

app.Run();                                         // ⑤ start Kestrel and block
""", "Program.cs")}
{tip("The <code>var app = builder.Build()</code> line is the boundary: services before it, middleware after it.")}

<h3>2. How middleware executes</h3>
<p>Think of a stack of functions. The pipeline runs in-order going in; then the same components run in reverse order on the way back out.</p>
{C(r"""
// Inline middleware with Use — runs both on the way in and the way out
app.Use(async (ctx, next) =>
{{
    Console.WriteLine($"→ {ctx.Request.Path}");   // executes on the WAY IN
    await next(ctx);                               // call the next middleware
    Console.WriteLine($"← {ctx.Response.StatusCode}"); // executes on the WAY OUT
}});

// Terminal middleware: never calls next
app.Run(async ctx =>
{{
    await ctx.Response.WriteAsync("नमस्ते! TodoAPI is running.");
}});

// Output for GET /:
//   → /
//   ← 200
""", "Program.cs")}

<h3>3. Class-based middleware</h3>
<p>Inline lambdas are fine for quick experiments, but for anything that needs DI or unit-testing, write a class.</p>
{C(r"""
// The middleware class — lives in /Middleware/RequestTimingMiddleware.cs
public class RequestTimingMiddleware(RequestDelegate next, ILogger<RequestTimingMiddleware> logger)
{{
    public async Task InvokeAsync(HttpContext ctx)
    {{
        var sw = System.Diagnostics.Stopwatch.StartNew();
        await next(ctx);                               // inner pipeline runs here
        sw.Stop();
        logger.LogInformation("{Method} {Path} → {Status} in {Ms} ms",
            ctx.Request.Method, ctx.Request.Path,
            ctx.Response.StatusCode, sw.ElapsedMilliseconds);
    }}
}}

// Extension method (optional but idiomatic)
public static class RequestTimingExtensions
{{
    public static IApplicationBuilder UseRequestTiming(this IApplicationBuilder app)
        => app.UseMiddleware<RequestTimingMiddleware>();
}}
""", "Middleware/RequestTimingMiddleware.cs")}
{C(r"""
// Register in Program.cs — BEFORE MapControllers or MapGet
app.UseRequestTiming();
""", "Program.cs (excerpt)")}
{tip("If the middleware needs a scoped service, inject it into <code>InvokeAsync</code> as a parameter — not into the constructor — because the middleware itself is a singleton.")}

<h3>4. Use / Run / Map</h3>
{C(r"""
// Use — chains middleware
app.Use(async (ctx, next) => {{ /* before */ await next(ctx); /* after */ }});

// Run — terminal, nothing after it runs
app.Run(async ctx => await ctx.Response.WriteAsync("Done"));

// Map — branches on path prefix; each branch gets its own sub-pipeline
app.Map("/health", branch =>
{{
    branch.Run(async ctx =>
    {{
        ctx.Response.ContentType = "application/json";
        await ctx.Response.WriteAsync(QQQ{{"status":"ok"}}QQQ);
    }});
}});

// MapWhen — branches on any predicate (e.g. header value)
app.MapWhen(ctx => ctx.Request.Headers.ContainsKey("X-Internal"),
    branch => branch.Run(async ctx => await ctx.Response.WriteAsync("internal path")));
""", "Program.cs")}

<h3>5. launchSettings.json and environments</h3>
{C(r"""
{{
  "profiles": {{
    "http": {{
      "commandName": "Project",
      "launchBrowser": false,
      "applicationUrl": "http://localhost:5100",
      "environmentVariables": {{
        "ASPNETCORE_ENVIRONMENT": "Development"
      }}
    }},
    "https": {{
      "applicationUrl": "https://localhost:7100;http://localhost:5100",
      "environmentVariables": {{
        "ASPNETCORE_ENVIRONMENT": "Development"
      }}
    }}
  }}
}}
""", "Properties/launchSettings.json", lang="json")}
{C(r"""
// Use env guards in Program.cs
if (app.Environment.IsDevelopment())
{{
    app.UseDeveloperExceptionPage();   // rich error page; never in production!
}}

// Or inline
app.UseWhen(ctx => !ctx.Request.Path.StartsWithSegments("/health"),
    branch => branch.UseRequestTiming());

// Three built-in environments; you can add your own (e.g. "Staging", "UAT")
// Set via env var:  ASPNETCORE_ENVIRONMENT=Production dotnet run
// Or launchSettings, appsettings.<env>.json is merged automatically.
""", "Program.cs")}

<h3>6. Correct middleware order</h3>
{table(["Middleware","Why its position matters"],[
["<code>UseExceptionHandler / UseDeveloperExceptionPage</code>","Must be first so it catches exceptions from everything downstream"],
["<code>UseHsts / UseHttpsRedirection</code>","Early, before anything writes to the response"],
["<code>UseStaticFiles</code>","Before routing — serves .css/.js without hitting the endpoint pipeline"],
["<code>UseRouting</code>","Populates <code>RouteData</code>; auth and policy need it"],
["<code>UseAuthentication</code>","After routing (needs the matched endpoint metadata for some schemes)"],
["<code>UseAuthorization</code>","After authentication"],
["<code>MapControllers / MapGet / …</code>","Last — the actual endpoint executers"]])}
''',
["Registering <code>UseAuthentication</code> before <code>UseRouting</code> (some schemes rely on endpoint metadata).",
"Writing <code>app.Use</code> after <code>app.Run</code> — it's unreachable.",
"Calling <code>await next(ctx)</code> more than once per request.",
"Injecting a scoped service into middleware constructor instead of <code>InvokeAsync</code>.",
"Forgetting to call <code>await next(ctx)</code> in a Use middleware and silently short-circuiting."],
("40 min", [
    "Create a blank <code>dotnet new web -n TodoApi</code>; add a <code>RequestTimingMiddleware</code> that logs method, path and elapsed ms.",
    "Add a <code>/health</code> branch with <code>Map</code> that returns <code>{{\"status\":\"ok\",\"env\":\"...\"}}</code> as JSON.",
    "Verify the middleware order produces in/out log pairs correctly by adding two <code>Use</code> blocks."]),
[("What does <code>await next(ctx)</code> do?","It hands control to the next middleware in the pipeline. Code before it runs on the way in; code after it runs on the way out."),
("What is the difference between Use and Run?","Both add middleware. Use chains to the next component (by calling next). Run is terminal — it never calls next and ends the pipeline."),
("What env variable controls the environment name?","<code>ASPNETCORE_ENVIRONMENT</code>. Common values are Development, Staging, Production. <code>app.Environment.IsDevelopment()</code> checks it.")],
[("Basic","What is Kestrel?","Kestrel is ASP.NET Core's built-in, cross-platform HTTP server. It listens on TCP, parses HTTP, and feeds requests into the middleware pipeline. It's production-capable and can sit behind a reverse proxy (Nginx, IIS, YARP) for TLS termination."),
("Basic","What is middleware and how is the pipeline ordered?","Middleware is a function that processes an HttpContext and optionally calls the next function. Components are added in order — first registered runs first on the way in and last on the way out. Order is critical: exception handling must be first, auth before authorisation, routing before endpoints."),
("Basic","Explain Use vs Run vs Map.","Use adds a middleware that may call next(). Run adds a terminal middleware that never calls next. Map branches the pipeline on a path prefix, giving the branch its own sub-pipeline."),
("Intermediate","What is the minimal hosting model and why was Startup.cs removed?","Starting in .NET 6, WebApplication.CreateBuilder and WebApplication replace the separate Startup class. Services and middleware can be configured in one place (Program.cs), reducing boilerplate and aligning with C# top-level statements."),
("Intermediate","How do you inject a scoped service into middleware?","Add it as a parameter to <code>InvokeAsync</code>, not to the constructor. Middleware is a singleton; injecting a scoped service into the constructor would capture it for the application lifetime, causing bugs."),
("Intermediate","How does ASP.NET Core find the right appsettings file?","<code>appsettings.json</code> is always loaded. Then <code>appsettings.{Environment}.json</code> is loaded and merged on top. If a key exists in both, the environment-specific file wins.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Dependency Injection Lifetimes",
"Master Singleton, Scoped and Transient lifetimes with concrete instance-ID demos, understand the captive dependency trap, and use IServiceScopeFactory and keyed services (.NET 8).",
[("DI container","The built-in <code>IServiceCollection</code> / <code>IServiceProvider</code> that creates and manages objects."),
("Singleton","One instance for the entire app lifetime. Shared by every request and every thread."),
("Scoped","One instance per HTTP request (or per manually created scope). The right lifetime for DbContext."),
("Transient","A new instance every time it is resolved. Cheap, stateless services."),
("Service descriptor","An entry in <code>IServiceCollection</code> describing a service type, its implementation, and lifetime."),
("Captive dependency","A singleton that holds a scoped or transient service, keeping it alive longer than intended."),
("ValidateScopes","DI option that detects captive dependency bugs at startup in Development."),
("ValidateOnStart","Checks that every registered service can be resolved at startup, not on the first request."),
("IServiceScopeFactory","Lets you create a DI scope manually — useful inside background services or singletons."),
("IEnumerable&lt;T&gt; injection","Inject all registrations of an interface. Last <code>AddX</code> call wins the single-inject slot."),
("Keyed services",".NET 8: register multiple implementations of the same interface under different string/enum keys."),
("InstanceId","A <code>Guid</code> set at construction, useful to prove which instance is returned.")],
["Scoped is the default for services that use <code>DbContext</code> — one per request = one transaction.",
"Singleton services must be thread-safe — they can be called by many threads concurrently.",
"<code>builder.Services.AddScoped&lt;T&gt;()</code> is the most common registration.",
"Use <code>TryAdd*</code> family to register a default that can be overridden (useful in libraries).",
"Calling <code>provider.GetRequiredService&lt;T&gt;()</code> throws if T isn't registered — good for startup failure."],
f'''
<h3>1. Instance-ID demo — proving lifetimes</h3>
{C(r"""
// Services/Traceable.cs — base service with a visible instance ID
public interface ITraceable {{ Guid Id {{ get; }} }}

public class SingletonService : ITraceable
{{
    public Guid Id {{ get; }} = Guid.NewGuid();     // set once at construction
}}
public class ScopedService : ITraceable
{{
    public Guid Id {{ get; }} = Guid.NewGuid();
}}
public class TransientService : ITraceable
{{
    public Guid Id {{ get; }} = Guid.NewGuid();
}}
""", "Services/Traceable.cs")}
{C(r"""
// Program.cs registrations
builder.Services.AddSingleton<SingletonService>();
builder.Services.AddScoped<ScopedService>();
builder.Services.AddTransient<TransientService>();

// Minimal API endpoint to inspect lifetimes
app.MapGet("/lifetimes", (
    SingletonService  s1,
    SingletonService  s2,   // same instance
    ScopedService     sc1,
    ScopedService     sc2,  // same instance within THIS request
    TransientService  t1,
    TransientService  t2    // different instances every time
) =>
{{
    return new
    {{
        singleton_same  = s1.Id == s2.Id,   // true
        scoped_same     = sc1.Id == sc2.Id, // true
        transient_same  = t1.Id == t2.Id,   // false
        singleton_id    = s1.Id,
        scoped_id       = sc1.Id,
    }};
}});
// Two requests in a row: singleton_id stays the same, scoped_id changes.
""", "Program.cs")}

<h3>2. Captive dependency and ValidateScopes</h3>
{C(r"""
// ❌ CAPTIVE DEPENDENCY — catches the scoped service in a singleton's lifetime
public class BadSingletonService(ScopedService scoped)
{{
    // The first request's ScopedService stays alive for the entire app lifetime
    // Every request after the first reuses stale state — including stale DbContext!
}}

// In Development, turning on ValidateScopes catches this at Build() time:
builder.Host.UseDefaultServiceProvider(o =>
{{
    o.ValidateScopes  = true;   // detect scoped-in-singleton at startup
    o.ValidateOnStart = true;   // ensure every service can be resolved at startup
}});
// Throws: "Cannot consume scoped service 'ScopedService' from singleton 'BadSingletonService'"
""", "Program.cs")}
{warn("ValidateScopes is enabled automatically in Development when you call <code>WebApplication.CreateBuilder</code> — but adding it explicitly with <code>ValidateOnStart=true</code> gives you earlier failure on misconfigured registrations.")}

<h3>3. IServiceScopeFactory — creating a scope manually</h3>
<p>Background services (<code>IHostedService</code>) are singletons. They need IServiceScopeFactory to resolve scoped services per work item.</p>
{C(r"""
// A hosted service that processes GST reminders on a schedule
public class GstReminderService(IServiceScopeFactory scopeFactory, ILogger<GstReminderService> logger)
    : BackgroundService
{{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {{
        while (!ct.IsCancellationRequested)
        {{
            await using var scope = scopeFactory.CreateAsyncScope();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();  // scoped!
            var dueCount = await db.Todos
                .Where(t => t.DueDate <= DateOnly.FromDateTime(DateTime.Today) && !t.IsDone)
                .CountAsync(ct);
            logger.LogInformation("{Count} GST/tax items are due today", dueCount);

            await Task.Delay(TimeSpan.FromHours(1), ct);
        }}
    }}
}}
""", "Services/GstReminderService.cs")}

<h3>4. Multiple registrations and IEnumerable&lt;T&gt;</h3>
{C(r"""
// Three notification channels for a payment gateway
public interface INotifier {{ Task NotifyAsync(string message); }}
public class EmailNotifier  : INotifier {{ public Task NotifyAsync(string m) {{ Console.WriteLine($"[Email] {{m}}"); return Task.CompletedTask; }} }}
public class SmsNotifier    : INotifier {{ public Task NotifyAsync(string m) {{ Console.WriteLine($"[SMS]   {{m}}"); return Task.CompletedTask; }} }}
public class WhatsAppNotifier: INotifier {{ public Task NotifyAsync(string m) {{ Console.WriteLine($"[WA]    {{m}}"); return Task.CompletedTask; }} }}

// Register all three
builder.Services.AddScoped<INotifier, EmailNotifier>();
builder.Services.AddScoped<INotifier, SmsNotifier>();
builder.Services.AddScoped<INotifier, WhatsAppNotifier>();

// Inject IEnumerable<INotifier> to get all three
app.MapPost("/notify", async (IEnumerable<INotifier> notifiers, string message) =>
{{
    foreach (var n in notifiers) await n.NotifyAsync(message);
    return Results.Ok();
}});

// Inject INotifier directly → you get WhatsAppNotifier (the last AddScoped wins)
""", "Program.cs")}

<h3>5. Keyed services (.NET 8)</h3>
{C(r"""
// Register under different keys — useful for strategy/factory patterns
builder.Services.AddKeyedScoped<INotifier, EmailNotifier>("email");
builder.Services.AddKeyedScoped<INotifier, SmsNotifier>("sms");
builder.Services.AddKeyedScoped<INotifier, WhatsAppNotifier>("whatsapp");

// Resolve by key in a minimal API endpoint
app.MapPost("/notify/{{channel}}", async (
    [FromKeyedServices("email")]    INotifier email,
    [FromKeyedServices("sms")]      INotifier sms,
    string channel, string message) =>
{{
    var notifier = channel switch
    {{
        "email" => email,
        "sms"   => sms,
        _       => throw new ArgumentException($"Unknown channel: {{channel}}")
    }};
    await notifier.NotifyAsync(message);
    return Results.Ok();
}});

// Or resolve programmatically from a scope
var notifier = scope.ServiceProvider.GetRequiredKeyedService<INotifier>("whatsapp");
""", "Program.cs")}
{tip("Keyed services replace the common pattern of injecting a factory function or dictionary of implementations.")}

<h3>6. Lifetime summary</h3>
{table(["Lifetime","Created","Shared","Typical use","Thread-safe?"],[
["Singleton","Once at first resolve","All requests, all threads","Config, caches, HttpClient factory","Must be"],
["Scoped","Once per request/scope","Within one request","DbContext, unit-of-work, current user","Only within the scope"],
["Transient","Every resolve","Never","Lightweight stateless helpers, formatters","N/A (new each time)"]])}
''',
["Injecting a scoped service into a singleton (captive dependency — DbContext in a singleton is a classic bug).",
"Making a singleton that caches per-request data (all requests share the same state).",
"Forgetting that transient instances aren't disposed until the scope ends (not immediately).",
"Using <code>GetService&lt;T&gt;</code> (returns null) where <code>GetRequiredService&lt;T&gt;</code> (throws) is safer.",
"Registering the same service twice with <code>AddScoped</code> when you meant to override with <code>TryAddScoped</code>."],
("40 min", [
    "Add <code>SingletonService</code>, <code>ScopedService</code>, <code>TransientService</code> to your TodoApi and hit the <code>/lifetimes</code> endpoint twice — confirm singleton ID stays the same.",
    "Intentionally create a captive dependency and confirm <code>ValidateScopes=true</code> catches it at <code>builder.Build()</code>.",
    "Register three <code>INotifier</code> implementations and inject <code>IEnumerable&lt;INotifier&gt;</code> to broadcast a message."]),
[("What is a captive dependency?","When a longer-lived service (Singleton) holds a shorter-lived service (Scoped/Transient), keeping it alive beyond its intended scope, causing stale state and resource leaks."),
("Why is Scoped the right lifetime for DbContext?","One DbContext per request = one database connection, one transaction, one change-tracker. Sharing it across requests would mix transactions."),
("How do you use a scoped service from a background service?","Inject IServiceScopeFactory into the background service (which is a singleton), then call CreateAsyncScope() per work item and resolve the scoped service from scope.ServiceProvider.")],
[("Basic","What are the three DI lifetimes in ASP.NET Core?","Singleton (one instance for the whole app), Scoped (one per HTTP request or manual scope), Transient (new instance every time it's resolved). Register with AddSingleton, AddScoped, AddTransient."),
("Basic","Why can't you inject a Scoped service into a Singleton?","The Singleton is created once and lives for the app's lifetime. The Scoped service's scope (the request) ends, but the Singleton still holds a reference to it, keeping it alive and stale. This is the captive dependency bug."),
("Basic","How do you register and resolve all implementations of an interface?","Register each with AddScoped/AddSingleton/AddTransient on the same interface. Inject <code>IEnumerable&lt;T&gt;</code> to get all of them. Direct injection of T returns only the last registration."),
("Intermediate","What is ValidateScopes and when should you enable it?","A DI option that checks at Build() time that no Singleton captures a Scoped dependency. It's auto-enabled in Development but you should also enable ValidateOnStart to catch all resolution errors at startup, not on the first request."),
("Intermediate","What are keyed services in .NET 8?","A way to register multiple implementations of the same interface under different string/enum keys, then resolve the right one by key using [FromKeyedServices(key)] in endpoints or GetRequiredKeyedService<T>(key) programmatically. Replaces factory/dictionary patterns."),
("Intermediate","When would you use IServiceScopeFactory?","When a singleton or background service needs to consume scoped services. Create a scope per unit of work (e.g. per message, per job), resolve scoped services from it, and dispose the scope when done.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Configuration and Options",
"Layer configuration sources correctly, bind strongly typed options, choose between IOptions/IOptionsSnapshot/IOptionsMonitor, and validate at startup.",
[("IConfiguration","The runtime view of all configuration sources merged together."),
("appsettings.json","Base configuration file, always loaded."),
("appsettings.{Environment}.json","Environment-specific overrides loaded on top."),
("Environment variables","Override any config key at deploy time. Double underscore <code>__</code> acts as a nesting separator."),
("Command-line args","Override at run time: <code>dotnet run --Smtp:Port=587</code>."),
("User secrets","Development-only secrets stored outside the project, never committed to git."),
("Options pattern","Bind a config section to a typed POCO via <code>Configure&lt;T&gt;</code>."),
("IOptions&lt;T&gt;","Singleton. Reads config once at startup. Use for settings that never change."),
("IOptionsSnapshot&lt;T&gt;","Scoped. Re-reads config per request. Use for settings that reload at runtime."),
("IOptionsMonitor&lt;T&gt;","Singleton with change notification via <code>OnChange</code>."),
("ValidateDataAnnotations","Validates options POCOs with <code>[Required]</code>, <code>[Range]</code> etc. at startup."),
("ValidateOnStart","Triggers validation at startup instead of first use.")],
["Config key lookup is case-insensitive.",
"<code>__</code> in env var names maps to <code>:</code> in config keys: <code>Smtp__Port=587</code> sets <code>Smtp:Port</code>.",
"User secrets are keyed to the project's <code>&lt;UserSecretsId&gt;</code> in the .csproj.",
"Never put real credentials in appsettings.json — use user-secrets in dev, Key Vault / env vars in prod.",
"<code>IOptions&lt;T&gt;</code> is a singleton — the same instance is returned across the app lifetime."],
f'''
<h3>1. Configuration layering</h3>
<p>WebApplication.CreateBuilder loads sources in this order (later sources win):</p>
{table(["Priority","Source","When to use"],[
["1 (lowest)","<code>appsettings.json</code>","Defaults shared across all envs"],
["2","<code>appsettings.{{Environment}}.json</code>","Env-specific overrides (dev URLs, test DBs)"],
["3","User secrets (dev only)","Credentials on dev machines"],
["4","Environment variables","Deployment-time overrides (CI/CD, Docker)"],
["5 (highest)","Command-line args","Run-time overrides"]])}
{C(r"""
// appsettings.json
{{
  "App": {{
    "Name": "TodoAPI",
    "MaxPageSize": 50,
    "AllowedOrigins": ["http://localhost:3000"]
  }},
  "Smtp": {{
    "Host": "smtp.gmail.com",
    "Port": 587,
    "From": "noreply@example.com",
    "Password": ""       // empty here — override via user-secrets or env var
  }}
}}
""", "appsettings.json", lang="json")}
{C(r"""
// appsettings.Development.json — merged on top of the base in Development
{{
  "Logging": {{
    "LogLevel": {{
      "Default": "Debug",
      "Microsoft.AspNetCore": "Information"
    }}
  }},
  "App": {{
    "MaxPageSize": 200    // higher limit in dev
  }}
}}
""", "appsettings.Development.json", lang="json")}

<h3>2. User secrets</h3>
{C(r"""
# Init user secrets (adds <UserSecretsId> to .csproj)
dotnet user-secrets init

# Set a secret — stored in ~/.microsoft/usersecrets/<id>/secrets.json  (never in the project)
dotnet user-secrets set "Smtp:Password" "mySecretGmailAppPassword"
dotnet user-secrets set "ConnectionStrings:Default" "Server=localhost;Database=TodoDb;..."

# List and remove
dotnet user-secrets list
dotnet user-secrets remove "Smtp:Password"
""", lang="bash")}

<h3>3. Env vars with __ nesting</h3>
{C(r"""
# Docker Compose or CI/CD — override nested config keys using __
# Smtp:Port  →  Smtp__Port
# App:Name   →  App__Name

# docker-compose.yml
# environment:
#   - Smtp__Password=myDockerPassword
#   - App__MaxPageSize=100
#   - ConnectionStrings__Default=Server=sqlserver;Database=TodoDb;...

# Or in a shell
export Smtp__Password="myPassword"
dotnet run
""", lang="bash")}

<h3>4. Options pattern — typed POCO binding</h3>
{C(r"""
// Options/AppOptions.cs
public class AppOptions
{{
    public const string Section = "App";

    [Required] public string Name {{ get; init; }} = "";
    [Range(1, 1000)] public int MaxPageSize {{ get; init; }} = 50;
    public List<string> AllowedOrigins {{ get; init; }} = [];
}}

public class SmtpOptions
{{
    public const string Section = "Smtp";

    [Required] public string Host {{ get; init; }} = "";
    [Range(1, 65535)] public int Port {{ get; init; }} = 587;
    [Required][EmailAddress] public string From {{ get; init; }} = "";
    public string Password {{ get; init; }} = "";
}}
""", "Options/AppOptions.cs")}
{C(r"""
// Program.cs — bind and validate at startup
builder.Services
    .AddOptions<AppOptions>()
    .BindConfiguration(AppOptions.Section)
    .ValidateDataAnnotations()
    .ValidateOnStart();         // fail fast at startup, not on first use

builder.Services
    .AddOptions<SmtpOptions>()
    .BindConfiguration(SmtpOptions.Section)
    .ValidateDataAnnotations()
    .ValidateOnStart();
""", "Program.cs")}

<h3>5. IOptions vs IOptionsSnapshot vs IOptionsMonitor</h3>
{C(r"""
// All three inject the same POCO but differ in when they re-read config:

// 1. IOptions<T> — singleton, config loaded once, never updates
app.MapGet("/options/app", (IOptions<AppOptions> opts) =>
    new {{ opts.Value.Name, opts.Value.MaxPageSize }});

// 2. IOptionsSnapshot<T> — scoped, re-reads per request (useful when you reload appsettings)
app.MapGet("/options/app/snap", (IOptionsSnapshot<AppOptions> opts) =>
    new {{ opts.Value.Name, opts.Value.MaxPageSize }});

// 3. IOptionsMonitor<T> — singleton, change notifications, great for long-running services
public class FeatureFlagService(IOptionsMonitor<AppOptions> monitor)
{{
    private AppOptions _current = monitor.CurrentValue;

    // ctor
    public FeatureFlagService(IOptionsMonitor<AppOptions> monitor) : this(monitor)
    {{
        monitor.OnChange(updated => _current = updated);   // hot-reload callback
    }}

    public bool CanShowDebugInfo => _current.Name.Contains("dev", StringComparison.OrdinalIgnoreCase);
}}
""", "Program.cs")}
{table(["","IOptions&lt;T&gt;","IOptionsSnapshot&lt;T&gt;","IOptionsMonitor&lt;T&gt;"],[
["Lifetime","Singleton","Scoped","Singleton"],
["When config reads","Once at startup","Every request","On change"],
["Change notification","No","No","Yes (OnChange)"],
["Inject into singleton","Yes","No","Yes"],
["Use for","Stable settings","Per-request reloadable","Hot-reload, feature flags"]])}

<h3>6. Reading config directly (without options)</h3>
{C(r"""
// Sometimes you just need a single value — read it inline
var connStr = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("Connection string 'Default' not configured.");

var maxPageSize = builder.Configuration.GetValue<int>("App:MaxPageSize", defaultValue: 50);

// Bind a whole section to a POCO without DI (useful in Startup / Program)
var smtpOptions = builder.Configuration
    .GetSection(SmtpOptions.Section)
    .Get<SmtpOptions>() ?? new SmtpOptions();
""", "Program.cs")}
''',
["Putting secrets in appsettings.json and committing them to git.",
"Using <code>IOptions&lt;T&gt;</code> for settings that change at runtime — use IOptionsMonitor.",
"Injecting <code>IOptionsSnapshot&lt;T&gt;</code> into a singleton (it's scoped).",
"Forgetting <code>ValidateOnStart</code> so a misconfigured SMTP host only errors on first send.",
"Using <code>:</code> as separator in environment variable names on Linux — use <code>__</code> instead."],
("40 min", [
    "Add <code>AppOptions</code> to your TodoApi with <code>MaxPageSize</code> and <code>AllowedOrigins</code>; validate at startup.",
    "Override <code>MaxPageSize</code> using <code>dotnet user-secrets</code> and confirm it takes effect.",
    "Inject <code>IOptions&lt;AppOptions&gt;</code> into a <code>/config</code> endpoint and return the values as JSON."]),
[("Which config source wins when the same key appears in appsettings.json and an env var?","The env var wins — it has higher priority in the default load order."),
("How do you nest config keys in environment variables?","Use double underscore <code>__</code> as the separator: <code>Smtp__Port=587</code> maps to <code>Smtp:Port</code>."),
("What is ValidateOnStart?","An options extension that triggers validation of the POCO at <code>Build()</code> time, so the app refuses to start rather than failing on the first request that uses the setting.")],
[("Basic","What is the options pattern in ASP.NET Core?","A way to bind a named configuration section to a strongly typed POCO class and inject it via IOptions&lt;T&gt;, IOptionsSnapshot&lt;T&gt; or IOptionsMonitor&lt;T&gt;, giving compile-time safety instead of stringly typed config lookups."),
("Basic","When should you use IOptionsSnapshot vs IOptions?","Use IOptions for settings that don't change while the app is running. Use IOptionsSnapshot when settings might be reloaded at runtime (e.g. appsettings.json edited without restart) — it re-reads per request because it's Scoped."),
("Basic","How do you store secrets in development without committing them to git?","Use <code>dotnet user-secrets</code>. Secrets are stored in a user-profile directory keyed to the project's UserSecretsId, never in the source tree."),
("Intermediate","What does ValidateDataAnnotations do for options?","It runs data annotation validators ([Required], [Range], [EmailAddress]) against the bound POCO when the options are first resolved. Combined with ValidateOnStart, it fails the app at startup if configuration is invalid."),
("Intermediate","How does IOptionsMonitor support hot-reload?","It monitors the config sources for changes and raises an OnChange callback whenever they reload. Services that need to react to live config changes (feature flags, connection pools) subscribe to that callback."),
("Intermediate","What is the config hierarchy in WebApplication.CreateBuilder?","appsettings.json → appsettings.{Environment}.json → user secrets (dev) → environment variables → command-line args. Each source overrides the previous. Environment variables use __ for nesting on Linux.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Minimal APIs",
"Map endpoints with MapGet/MapPost/MapPut/MapDelete, use route constraints and binding sources, return TypedResults, group endpoints with MapGroup, add endpoint filters, and shape ProblemDetails errors.",
[("Minimal API","A lightweight way to define HTTP endpoints directly in Program.cs without controller classes."),
("MapGet / MapPost / MapPut / MapDelete / MapPatch","Extension methods that register an endpoint for the given HTTP verb and route pattern."),
("Route parameter","A segment in curly braces: <code>/todos/{{id}}</code>. Bound to a handler parameter by name."),
("Route constraint","A type or regex in a route segment: <code>{{id:int}}</code>, <code>{{slug:alpha}}</code>."),
("Binding source","Where ASP.NET Core looks for a parameter value: route, query, body, header, services."),
("[AsParameters]","Tells the binder to populate a struct/record's properties from the same sources as top-level params."),
("TypedResults","Static factory methods (<code>TypedResults.Ok</code>, <code>TypedResults.NotFound</code>) that return a typed <code>IResult</code>."),
("Results&lt;T1,T2&gt;","Union return type for endpoints that can return more than one result type (.NET 7+)."),
("MapGroup","Groups endpoints under a shared prefix and lets you apply filters, auth, etc. once."),
("IEndpointFilter","An interface for middleware-like logic scoped to one endpoint or group."),
("ProblemDetails","RFC 7807 JSON error format: <code>type</code>, <code>title</code>, <code>status</code>, <code>detail</code>, <code>instance</code>.")],
["Minimal APIs have no <code>[ApiController]</code> automatic model validation — you do it explicitly (Saturday).",
"Query strings are bound automatically when a parameter has no route segment or body attribute.",
"<code>TypedResults.Ok(value)</code> sets Content-Type application/json + 200; prefer it over raw <code>Results.Ok</code> for OpenAPI schema."],
f'''
<h3>1. MapGet / MapPost / MapPut / MapDelete</h3>
{C(r"""
// The four verbs + a minimal route
app.MapGet   ("/todos",        () => "list all");
app.MapPost  ("/todos",        () => "create");
app.MapPut   ("/todos/{{id}}",   (int id) => $"update {{id}}");
app.MapDelete("/todos/{{id}}",   (int id) => $"delete {{id}}");
app.MapPatch ("/todos/{{id}}",   (int id) => $"patch {{id}}");

// Handler can be async
app.MapGet("/todos/{{id}}", async (int id, AppDbContext db) =>
{{
    var item = await db.Todos.FindAsync(id);
    return item is null ? Results.NotFound() : Results.Ok(item);
}});
""", "Program.cs")}

<h3>2. Route constraints and binding sources</h3>
{C(r"""
// Route constraints — 400 if the value doesn't satisfy the constraint
app.MapGet("/todos/{{id:int:min(1)}}", (int id) => $"id={{id}}");
app.MapGet("/files/{{name:alpha:maxlength(50)}}", (string name) => $"file={{name}}");

// Binding sources — where each parameter comes from
app.MapGet("/search", (
    string? title,                              // from query: /search?title=GST
    [FromHeader(Name="X-Page")] int page = 1,  // from header
    [FromRoute] int? categoryId = null          // explicitly from route
) => $"title={{title}} page={{page}}");

// Body binding — the SINGLE body is deserialized automatically
app.MapPost("/todos", async (CreateTodoDto dto, AppDbContext db) =>
{{
    // dto comes from the JSON body
}});

// [AsParameters] — bind a record from multiple sources at once (.NET 7+)
public record TodoQuery([FromQuery] string? Title, [FromQuery] int Page = 1, [FromQuery] int PageSize = 20);

app.MapGet("/todos", ([AsParameters] TodoQuery q) =>
    $"title={{q.Title}} page={{q.Page}} size={{q.PageSize}}");
""", "Program.cs")}

<h3>3. TypedResults and Results&lt;T1,T2&gt;</h3>
{C(r"""
// Results.Ok() returns IResult — no schema info for OpenAPI
// TypedResults.Ok() returns Ok<T> which carries the type for Swagger

app.MapGet("/todos/{{id:int}}", async (int id, AppDbContext db) =>
{{
    var item = await db.Todos.FindAsync(id);
    return item is null
        ? TypedResults.NotFound()
        : TypedResults.Ok(item);
    // return type inferred as Results<Ok<TodoItem>, NotFound>
}});

// Explicit union return type — good for OpenAPI documentation
app.MapPost("/todos", async (CreateTodoDto dto, AppDbContext db)
    : Task<Results<Created<TodoItem>, ValidationProblem>> =>
{{
    if (string.IsNullOrWhiteSpace(dto.Title))
        return TypedResults.ValidationProblem(new Dictionary<string, string[]>
        {{
            ["title"] = ["Title is required"]
        }});

    var item = new TodoItem {{ Title = dto.Title, DueDate = dto.DueDate, Priority = dto.Priority }};
    db.Todos.Add(item);
    await db.SaveChangesAsync();
    return TypedResults.Created($"/todos/{{item.Id}}", item);
}});
""", "Program.cs")}
{table(["Factory method","Status code","Content-Type"],[
["<code>TypedResults.Ok(value)</code>","200","application/json"],
["<code>TypedResults.Created(uri, value)</code>","201","application/json"],
["<code>TypedResults.NoContent()</code>","204","—"],
["<code>TypedResults.NotFound()</code>","404","—"],
["<code>TypedResults.BadRequest(detail)</code>","400","application/json"],
["<code>TypedResults.ValidationProblem(errors)</code>","400","application/problem+json"],
["<code>TypedResults.Problem(detail, ...)</code>","500","application/problem+json"]])}

<h3>4. MapGroup — shared prefix and cross-cutting concerns</h3>
{C(r"""
// All todos endpoints grouped under /api/todos
var todos = app.MapGroup("/api/todos")
               .WithTags("Todos")            // Swagger tag
               .RequireAuthorization();      // applied to every endpoint in the group

todos.MapGet(   "/",          TodoHandlers.GetAll);
todos.MapGet(   "/{{id:int}}", TodoHandlers.GetById);
todos.MapPost(  "/",          TodoHandlers.Create);
todos.MapPut(   "/{{id:int}}", TodoHandlers.Update);
todos.MapDelete("/{{id:int}}", TodoHandlers.Delete);

// Groups can be nested
var v2 = app.MapGroup("/api/v2");
var v2Todos = v2.MapGroup("/todos");
""", "Program.cs")}

<h3>5. Endpoint filters</h3>
{C(r"""
// A filter runs before and after the endpoint handler — like middleware for one route
public class LoggingFilter : IEndpointFilter
{{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext ctx, EndpointFilterDelegate next)
    {{
        var method = ctx.HttpContext.Request.Method;
        var path   = ctx.HttpContext.Request.Path;
        Console.WriteLine($"→ {{method}} {{path}}");
        var result = await next(ctx);                // calls the handler (or the next filter)
        Console.WriteLine($"← {{ctx.HttpContext.Response.StatusCode}}");
        return result;
    }}
}}

// Attach to a group or a single endpoint
todos.AddEndpointFilter<LoggingFilter>();

// Inline filter
todos.MapPost("/", TodoHandlers.Create)
     .AddEndpointFilter(async (ctx, next) =>
     {{
         Console.WriteLine("inline filter before");
         var r = await next(ctx);
         Console.WriteLine("inline filter after");
         return r;
     }});
""", "Program.cs")}

<h3>6. ProblemDetails</h3>
{C(r"""
// Register ProblemDetails service — formats unhandled exceptions as RFC 7807 JSON
builder.Services.AddProblemDetails();

// In Program.cs pipeline — must be first
app.UseExceptionHandler();     // catches exceptions and uses IProblemDetailsService
app.UseStatusCodePages();      // turns 404/405 responses into problem+json

// Manually return ProblemDetails
app.MapGet("/bad", () =>
    TypedResults.Problem(
        detail: "फाइल नहीं मिली",
        statusCode: StatusCodes.Status422UnprocessableEntity,
        title: "Unprocessable Entity",
        type: "https://tools.ietf.org/html/rfc4918#section-11.2"
    ));

// Response:
// HTTP 422
// Content-Type: application/problem+json
// {{
//   "type":   "https://tools.ietf.org/html/rfc4918#section-11.2",
//   "title":  "Unprocessable Entity",
//   "status": 422,
//   "detail": "फाइल नहीं मिली"
// }}
""", "Program.cs")}
''',
["Returning a plain <code>string</code> from an endpoint and expecting JSON — it's served as text/plain.",
"Forgetting route constraints: <code>/todos/{id}</code> matches <code>/todos/abc</code>; use <code>{{id:int}}</code> to reject non-integers.",
"Using <code>Results.Ok</code> (no type info) instead of <code>TypedResults.Ok</code> (OpenAPI schema).",
"Calling <code>MapGroup</code> after the endpoint registrations — the group must be declared first.",
"Applying <code>RequireAuthorization</code> without registering the auth services."],
("40 min", [
    "Define <code>/api/todos</code> with MapGroup; add GET all, GET by id, POST, PUT, DELETE using TypedResults.",
    "Add a route constraint <code>{{id:int:min(1)}}</code> and test it with curl for a string id.",
    "Write an endpoint filter that validates the JSON Content-Type header on POST/PUT and returns 415 if missing."]),
[("How does query string binding work in minimal APIs?","A handler parameter with no route segment and no binding attribute is bound from the query string automatically, e.g. <code>(string? search)</code> reads <code>?search=…</code>."),
("What is the difference between TypedResults and Results?","Both return IResult. TypedResults returns a typed IResult (e.g. Ok&lt;T&gt;) so the OpenAPI/Swagger schema is generated from it. Results returns a non-generic IResult with no schema info."),
("What does MapGroup do?","Groups endpoints under a shared route prefix, and lets you apply filters, auth, metadata and tags once instead of on every endpoint.")],
[("Basic","How do you define a GET endpoint that returns JSON in a minimal API?","<code>app.MapGet(\"/path\", () => new {{ name = \"value\" }})</code> — anonymous objects are serialised to JSON. Use TypedResults.Ok(value) for explicit typing and OpenAPI schema."),
("Basic","What are route constraints and why use them?","Inline type checks in route patterns, like <code>{{id:int}}</code> or <code>{{name:alpha:maxlength(20)}}</code>. They return 404 or 400 before the handler runs if the value doesn't match, so the handler receives guaranteed-valid data."),
("Basic","What is ProblemDetails?","A standardised JSON error format defined by RFC 7807, returned by ASP.NET Core on errors. It has type, title, status, detail and instance fields. TypedResults.Problem() creates it."),
("Intermediate","What is an endpoint filter and how does it differ from middleware?","An endpoint filter (IEndpointFilter) is like middleware but scoped to a single endpoint or MapGroup, not the whole pipeline. It can inspect handler arguments (ctx.Arguments) and short-circuit before the handler. Middleware runs for every request regardless of the endpoint."),
("Intermediate","What is [AsParameters] used for?","It tells the minimal API binder to populate the properties of a record or struct from the same binding sources as individual handler parameters (route, query, header), so you can group them into a tidy request object without wrapping them in a body DTO."),
("Intermediate","How do Results&lt;T1,T2&gt; improve OpenAPI documentation?","The union return type gives Swashbuckle/NSwag the full list of possible response shapes and status codes for a single endpoint, instead of just IResult which produces no schema info.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Controllers",
"Use [ApiController] attribute routing, understand automatic 400 validation, return ActionResult&lt;T&gt;, and choose between controllers and minimal APIs.",
[("[ApiController]","Attribute that enables API-specific behaviour on a controller class: auto 400, binding inference, attribute routing required."),
("ControllerBase","Base class for API controllers. Provides helper methods like Ok(), NotFound(), BadRequest(), CreatedAtAction()."),
("[Route] attribute","Defines the route template for a controller or action."),
("[ApiController] automatic 400","When model binding or validation fails, [ApiController] returns a 400 ProblemDetails automatically — before the action runs."),
("ModelState","The validation dictionary populated by model binding and data annotations."),
("ActionResult&lt;T&gt;","A union return type that can be either T (auto 200) or any IActionResult (NotFound, BadRequest, etc.)."),
("[FromBody]","Explicitly bind a parameter from the JSON request body (implicit with [ApiController])."),
("[FromRoute] / [FromQuery]","Explicit source binding on action parameters."),
("CreatedAtAction","Returns 201 with a Location header pointing to the GET endpoint for the new resource."),
("ProducesResponseType","Documents expected status codes on an action for Swagger."),
("ControllerRoute token","<code>[controller]</code> in route templates is replaced by the controller class name minus 'Controller'.")],
["<code>[ApiController]</code> requires attribute routing — no convention-based routing.",
"<code>ModelState.IsValid</code> is checked automatically; don't re-check it unless you have a reason.",
"Return <code>ActionResult&lt;T&gt;</code> (not <code>IActionResult</code>) so Swagger sees the response schema.",
"Keep controllers thin: they translate HTTP to service calls and back, nothing else."],
f'''
<h3>1. Controller anatomy</h3>
{C(r"""
using Microsoft.AspNetCore.Mvc;

namespace TodoApi.Controllers;

[ApiController]
[Route("api/[controller]")]          // → api/todos
public class TodosController(TodoService svc) : ControllerBase
{{
    // GET api/todos
    [HttpGet]
    [ProducesResponseType<IEnumerable<TodoDto>>(200)]
    public async Task<ActionResult<IEnumerable<TodoDto>>> GetAll([FromQuery] string? title)
    {{
        var items = await svc.GetAllAsync(title);
        return Ok(items);
    }}

    // GET api/todos/5
    [HttpGet("{{id:int}}")]
    [ProducesResponseType<TodoDto>(200)]
    [ProducesResponseType(404)]
    public async Task<ActionResult<TodoDto>> GetById(int id)
    {{
        var item = await svc.GetByIdAsync(id);
        return item is null ? NotFound() : Ok(item);
    }}

    // POST api/todos
    [HttpPost]
    [ProducesResponseType<TodoDto>(201)]
    [ProducesResponseType(400)]
    public async Task<ActionResult<TodoDto>> Create(CreateTodoDto dto)
    {{
        // [ApiController] already returned 400 if dto is invalid
        var item = await svc.CreateAsync(dto);
        return CreatedAtAction(nameof(GetById), new {{ id = item.Id }}, item);
    }}

    // PUT api/todos/5
    [HttpPut("{{id:int}}")]
    [ProducesResponseType(204)]
    [ProducesResponseType(400)]
    [ProducesResponseType(404)]
    public async Task<IActionResult> Update(int id, UpdateTodoDto dto)
    {{
        var updated = await svc.UpdateAsync(id, dto);
        return updated ? NoContent() : NotFound();
    }}

    // DELETE api/todos/5
    [HttpDelete("{{id:int}}")]
    [ProducesResponseType(204)]
    [ProducesResponseType(404)]
    public async Task<IActionResult> Delete(int id)
    {{
        var deleted = await svc.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }}
}}
""", "Controllers/TodosController.cs")}

<h3>2. Automatic 400 — [ApiController] in action</h3>
{C(r"""
// DTO with data annotations
public record CreateTodoDto(
    [Required][MaxLength(200)] string Title,
    DateOnly? DueDate,
    Priority Priority = Priority.Medium
);

// Without [ApiController] you'd write:
// if (!ModelState.IsValid) return BadRequest(ModelState);

// WITH [ApiController] the framework does it automatically before the action runs.
// Invalid request → HTTP 400 ProblemDetails:
// {{
//   "type": "...",
//   "title": "One or more validation errors occurred.",
//   "status": 400,
//   "errors": {{
//     "Title": ["The Title field is required."]
//   }}
// }}
""", "Controllers/TodosController.cs")}

<h3>3. ActionResult&lt;T&gt; vs IActionResult</h3>
{C(r"""
// IActionResult — no schema info for Swagger
[HttpGet("{{id}}")]
public IActionResult GetOld(int id) => Ok(new TodoDto());    // Swagger: 200 → no schema

// ActionResult<T> — Swagger sees the T schema + other response types
[HttpGet("{{id}}")]
public ActionResult<TodoDto> GetNew(int id) => Ok(new TodoDto());    // Swagger: 200 → TodoDto

// ActionResult<T> implicit conversions:
// return item;        → 200 Ok with item serialised  (implicit from T)
// return Ok(item);    → same, explicit
// return NotFound();  → 404 (implicit from IActionResult)
""", "Controllers/TodosController.cs")}

<h3>4. Attribute routing tokens and sub-routes</h3>
{C(r"""
[ApiController]
[Route("api/v{{version:apiVersion}}/[controller]")]   // token + route constraint
public class OrdersController : ControllerBase
{{
    // GET api/v1/orders/{{orderId}}/lines
    [HttpGet("{{orderId:int}}/lines")]
    public ActionResult<IEnumerable<OrderLineDto>> GetLines(int orderId) => Ok(Array.Empty<OrderLineDto>());

    // POST api/v1/orders/{{orderId}}/lines
    [HttpPost("{{orderId:int}}/lines")]
    public ActionResult<OrderLineDto> AddLine(int orderId, CreateOrderLineDto dto) => CreatedAtAction(
        nameof(GetLines), new {{ orderId }}, new OrderLineDto());
}}
""", "Controllers/OrdersController.cs")}

<h3>5. Minimal APIs vs Controllers</h3>
{table(["","Minimal APIs","Controllers"],[
["Verbosity","Very low (3–5 lines per endpoint)","More ceremony (class + method + attributes)"],
["Organisation","Groups via MapGroup; handlers in static classes","One class per resource or area"],
["Automatic model validation","No (use endpoint filter or FluentValidation)","Yes — [ApiController] auto 400"],
["Testability","Harder to unit-test (need WebApplicationFactory)","Easier to unit-test in isolation"],
["OpenAPI/Swagger","Good (TypedResults, WithOpenApi())","Good ([ProducesResponseType], XML comments)"],
["Filters / middleware scoping","Endpoint filters per route/group","Action filters, resource filters"],
["Recommended for","Simple services, micro-services, rapid prototyping","Large APIs with many resources and business rules"],
["Available since",".NET 6","ASP.NET Core 1.0"]])}
{tip("Both styles can coexist in one project. This week uses minimal APIs; Week 18 uses controllers for the product catalog API so you can compare them in practice.")}
''',
["Using <code>Controller</code> (MVC base) instead of <code>ControllerBase</code> for an API — <code>Controller</code> includes View support you don't need.",
"Returning <code>IActionResult</code> instead of <code>ActionResult&lt;T&gt;</code> — Swagger loses the response schema.",
"Naming a DTO parameter the same as a route parameter — binding picks up the wrong source.",
"Calling <code>Ok(null)</code> for a not-found — return <code>NotFound()</code> for 404 semantics.",
"Forgetting <code>[ApiController]</code> and wondering why validation doesn't return 400 automatically."],
("40 min", [
    "Rewrite the minimal API todos endpoint from Thursday as a <code>TodosController</code>.",
    "Add data annotations to <code>CreateTodoDto</code> and confirm that an empty Title returns a 400 ProblemDetails automatically.",
    "Use <code>CreatedAtAction</code> for the POST response and verify the <code>Location</code> header with curl."]),
[("What does [ApiController] do?","Enables attribute routing requirement, automatic 400 on invalid ModelState, binding source inference (body for complex types, query for simple types), and improved error responses."),
("Why return ActionResult&lt;T&gt; instead of IActionResult?","ActionResult&lt;T&gt; has implicit conversions from both T and IActionResult. It carries the T type info so Swagger/OpenAPI can generate the response schema for the 200 response."),
("What is CreatedAtAction?","A ControllerBase helper that returns HTTP 201 Created with a Location header pointing to the action that retrieves the newly created resource.")],
[("Basic","What is [ApiController] and what does it enable?","An attribute applied to a controller class that enables API-specific behaviours: attribute routing is required (no convention routing), model validation failures return 400 automatically before the action runs, and binding sources are inferred (complex params from body, simple from query/route)."),
("Basic","What is the difference between Ok(), NotFound(), and BadRequest()?","Helper methods on ControllerBase that return ObjectResult / NotFoundResult / BadRequestResult with the appropriate HTTP status codes (200, 404, 400). They set Content-Type and serialise the value to JSON."),
("Basic","What is ModelState?","A dictionary that model binding fills with the parameter values and any validation errors from data annotations. [ApiController] automatically checks IsValid and returns 400 before your action runs."),
("Intermediate","How does attribute routing work with [controller] token?","[Route(\"api/[controller]\")] replaces [controller] with the class name minus the 'Controller' suffix. TodosController → api/todos. You can also use [Route(\"api/todos\")] explicitly."),
("Intermediate","When would you choose minimal APIs over controllers?","Minimal APIs suit small services, micro-services and rapid prototyping where the per-endpoint code is a few lines. Controllers are better for large APIs where grouping by resource class, filters, action policies and unit-testing in isolation matter more."),
("Intermediate","How do you document multiple response types for Swagger?","Decorate actions with [ProducesResponseType<T>(200)], [ProducesResponseType(404)] etc. For minimal APIs, use TypedResults and Results<T1,T2> union return types which carry the type info automatically.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "TodoApi — Minimal API with EF Core",
"Build a full CRUD API for a TodoItem entity with SQLite (dev) or SQL Server (prod), DTOs, a /api/todos group, filtering, toggle, migrations and seed data.",
[("TodoItem","The entity: Id, Title, IsDone, DueDate, Priority (enum), CreatedAt."),
("Priority enum","<code>Low = 0, Medium = 1, High = 2, Critical = 3</code>."),
("AppDbContext","EF Core DbContext exposing <code>DbSet&lt;TodoItem&gt; Todos</code>."),
("DTO","Data Transfer Object — exposes only what the API consumer needs; isolates the entity from the contract."),
("MapGroup","Groups all <code>/api/todos</code> endpoints to avoid repeating the prefix."),
("Toggle endpoint","<code>PATCH /api/todos/{{id}}/toggle</code> flips IsDone."),
("Filter/search","<code>GET /api/todos?title=GST&amp;isDone=false&amp;priority=High</code>."),
("Migration","EF Core command (<code>dotnet ef migrations add</code>) that generates a C# snapshot of a schema change."),
("Seed","Initial data inserted if the table is empty; makes the API immediately testable.")],
["Use <code>&lt;FrameworkReference Include=\"Microsoft.AspNetCore.App\" /&gt;</code> + <code>Microsoft.EntityFrameworkCore.Sqlite</code> NuGet.",
"Keep DTOs separate from entities — never expose navigation properties directly.",
"<code>db.SaveChangesAsync()</code> must be awaited before reading back generated IDs.",
"Return 404 from both GetById and Update/Delete when the item doesn't exist.",
"Seed data only when the table is empty; use <code>db.Database.MigrateAsync()</code> to apply migrations at startup."],
f'''
<h3>Scaffold and project setup</h3>
{C(r"""
dotnet new web -n TodoApi
cd TodoApi

# EF Core + SQLite for dev, SQL Server for prod
dotnet add package Microsoft.EntityFrameworkCore.Sqlite      --version 8.0.*
dotnet add package Microsoft.EntityFrameworkCore.SqlServer   --version 8.0.*
dotnet add package Microsoft.EntityFrameworkCore.Design      --version 8.0.*

# Optional: Swashbuckle for Sunday
dotnet add package Swashbuckle.AspNetCore --version 6.*
""", lang="bash")}
{C(r"""
TodoApi/
├── Controllers/            (empty this week — minimal API)
├── Data/
│   └── AppDbContext.cs
├── DTOs/
│   ├── CreateTodoDto.cs
│   ├── UpdateTodoDto.cs
│   └── TodoDto.cs
├── Endpoints/
│   └── TodoEndpoints.cs    (handler methods)
├── Models/
│   └── TodoItem.cs
├── Middleware/
│   └── RequestTimingMiddleware.cs
├── Migrations/             (generated by dotnet ef)
├── Properties/
│   └── launchSettings.json
├── appsettings.json
├── appsettings.Development.json
└── Program.cs
""", lang="text")}

<h3>Step 1 — TodoItem model</h3>
{C(r"""
namespace TodoApi.Models;

public enum Priority {{ Low = 0, Medium = 1, High = 2, Critical = 3 }}

public class TodoItem
{{
    public int      Id        {{ get; set; }}
    public string   Title     {{ get; set; }} = "";
    public bool     IsDone    {{ get; set; }}
    public DateOnly? DueDate  {{ get; set; }}
    public Priority Priority  {{ get; set; }} = Priority.Medium;
    public DateTime CreatedAt {{ get; set; }} = DateTime.UtcNow;
}}
""", "Models/TodoItem.cs")}

<h3>Step 2 — AppDbContext</h3>
{C(r"""
using Microsoft.EntityFrameworkCore;
using TodoApi.Models;

namespace TodoApi.Data;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{{
    public DbSet<TodoItem> Todos => Set<TodoItem>();

    protected override void OnModelCreating(ModelBuilder mb)
    {{
        mb.Entity<TodoItem>(e =>
        {{
            e.Property(t => t.Title).HasMaxLength(200).IsRequired();
            e.Property(t => t.Priority).HasConversion<string>();  // store enum as string
            e.HasIndex(t => t.IsDone);                            // filter by done/not-done
        }});
    }}
}}
""", "Data/AppDbContext.cs")}

<h3>Step 3 — DTOs</h3>
{C(r"""
using System.ComponentModel.DataAnnotations;
using TodoApi.Models;

namespace TodoApi.DTOs;

// What the client sends when creating
public record CreateTodoDto(
    [Required][MaxLength(200)] string Title,
    DateOnly? DueDate,
    Priority Priority = Priority.Medium
);

// What the client sends when updating
public record UpdateTodoDto(
    [Required][MaxLength(200)] string Title,
    DateOnly? DueDate,
    Priority Priority
);

// What the API returns
public record TodoDto(int Id, string Title, bool IsDone, DateOnly? DueDate, Priority Priority, DateTime CreatedAt);

public static class TodoMappings
{{
    public static TodoDto ToDto(this TodoItem t)
        => new(t.Id, t.Title, t.IsDone, t.DueDate, t.Priority, t.CreatedAt);
}}
""", "DTOs/TodoDtos.cs")}

<h3>Step 4 — Endpoint handlers</h3>
{C(r"""
using Microsoft.EntityFrameworkCore;
using TodoApi.Data;
using TodoApi.DTOs;
using TodoApi.Models;

namespace TodoApi.Endpoints;

public static class TodoEndpoints
{{
    // GET /api/todos?title=&isDone=&priority=&page=1&pageSize=20
    public static async Task<IResult> GetAll(
        AppDbContext db,
        string? title    = null,
        bool?   isDone   = null,
        string? priority = null,
        int     page     = 1,
        int     pageSize = 20)
    {{
        var q = db.Todos.AsQueryable();
        if (!string.IsNullOrWhiteSpace(title))
            q = q.Where(t => t.Title.Contains(title));
        if (isDone.HasValue)
            q = q.Where(t => t.IsDone == isDone.Value);
        if (Enum.TryParse<Priority>(priority, ignoreCase: true, out var p))
            q = q.Where(t => t.Priority == p);

        var items = await q
            .OrderByDescending(t => t.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Select(t => t.ToDto())
            .ToListAsync();

        return TypedResults.Ok(items);
    }}

    // GET /api/todos/{id}
    public static async Task<IResult> GetById(int id, AppDbContext db)
    {{
        var item = await db.Todos.FindAsync(id);
        return item is null ? TypedResults.NotFound() : TypedResults.Ok(item.ToDto());
    }}

    // POST /api/todos
    public static async Task<IResult> Create(CreateTodoDto dto, AppDbContext db)
    {{
        var item = new TodoItem
        {{
            Title    = dto.Title,
            DueDate  = dto.DueDate,
            Priority = dto.Priority
        }};
        db.Todos.Add(item);
        await db.SaveChangesAsync();
        return TypedResults.Created($"/api/todos/{{item.Id}}", item.ToDto());
    }}

    // PUT /api/todos/{id}
    public static async Task<IResult> Update(int id, UpdateTodoDto dto, AppDbContext db)
    {{
        var item = await db.Todos.FindAsync(id);
        if (item is null) return TypedResults.NotFound();

        item.Title    = dto.Title;
        item.DueDate  = dto.DueDate;
        item.Priority = dto.Priority;
        await db.SaveChangesAsync();
        return TypedResults.Ok(item.ToDto());
    }}

    // DELETE /api/todos/{id}
    public static async Task<IResult> Delete(int id, AppDbContext db)
    {{
        var item = await db.Todos.FindAsync(id);
        if (item is null) return TypedResults.NotFound();
        db.Todos.Remove(item);
        await db.SaveChangesAsync();
        return TypedResults.NoContent();
    }}

    // PATCH /api/todos/{id}/toggle
    public static async Task<IResult> Toggle(int id, AppDbContext db)
    {{
        var item = await db.Todos.FindAsync(id);
        if (item is null) return TypedResults.NotFound();
        item.IsDone = !item.IsDone;
        await db.SaveChangesAsync();
        return TypedResults.Ok(item.ToDto());
    }}
}}
""", "Endpoints/TodoEndpoints.cs")}

<h3>Step 5 — Program.cs</h3>
{C(r"""
using Microsoft.EntityFrameworkCore;
using TodoApi.Data;
using TodoApi.Endpoints;
using TodoApi.Models;

var builder = WebApplication.CreateBuilder(args);

// DB: SQLite in dev, SQL Server in prod (driven by config)
var connStr = builder.Configuration.GetConnectionString("Default");
if (builder.Environment.IsDevelopment())
    builder.Services.AddDbContext<AppDbContext>(o => o.UseSqlite("Data Source=todo.db"));
else
    builder.Services.AddDbContext<AppDbContext>(o => o.UseSqlServer(connStr));

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// Migrate and seed on startup
using (var scope = app.Services.CreateScope())
{{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.MigrateAsync();

    if (!await db.Todos.AnyAsync())
    {{
        db.Todos.AddRange(
            new TodoItem {{ Title = "File GST return Q3",         DueDate = DateOnly.Parse("2026-01-20"), Priority = Priority.Critical }},
            new TodoItem {{ Title = "Pay EMI for home loan",       DueDate = DateOnly.Parse("2026-01-05"), Priority = Priority.High }},
            new TodoItem {{ Title = "Renew car insurance",         DueDate = DateOnly.Parse("2026-02-14"), Priority = Priority.Medium }},
            new TodoItem {{ Title = "Book CA for ITR filing",      DueDate = DateOnly.Parse("2026-07-31"), Priority = Priority.High }},
            new TodoItem {{ Title = "Transfer FD on maturity",     DueDate = DateOnly.Parse("2026-03-01"), Priority = Priority.Medium }},
            new TodoItem {{ Title = "Pay advance tax Q4",          DueDate = DateOnly.Parse("2026-03-15"), Priority = Priority.Critical }}
        );
        await db.SaveChangesAsync();
    }}
}}

if (app.Environment.IsDevelopment())
{{
    app.UseSwagger();
    app.UseSwaggerUI();
}}

app.UseHttpsRedirection();

// /api/todos group
var todos = app.MapGroup("/api/todos").WithTags("Todos");

todos.MapGet   ("/",              TodoEndpoints.GetAll);
todos.MapGet   ("/{{id:int}}",      TodoEndpoints.GetById);
todos.MapPost  ("/",              TodoEndpoints.Create);
todos.MapPut   ("/{{id:int}}",      TodoEndpoints.Update);
todos.MapDelete("/{{id:int}}",      TodoEndpoints.Delete);
todos.MapPatch ("/{{id:int}}/toggle", TodoEndpoints.Toggle);

app.Run();
""", "Program.cs")}

<h3>Step 6 — Migrations and run</h3>
{C(r"""
# Add EF Tools if not already installed
dotnet tool install --global dotnet-ef

# Generate the initial migration
dotnet ef migrations add InitialCreate

# (The app auto-runs MigrateAsync on startup, so no need to dotnet ef database update)
# Start the API
dotnet run
""", lang="bash")}

<h3>Step 7 — curl examples</h3>
{C(r"""
BASE=http://localhost:5100/api/todos

# Create a todo
curl -s -X POST $BASE \
  -H "Content-Type: application/json" \
  -d '{{"title":"File GST return Q3","dueDate":"2026-01-20","priority":"Critical"}}' | jq

# Expected:
# {{"id":1,"title":"File GST return Q3","isDone":false,"dueDate":"2026-01-20","priority":"Critical","createdAt":"..."}}

# List all
curl -s $BASE | jq

# Filter: only Critical items not done
curl -s "$BASE?priority=Critical&isDone=false" | jq

# Search by title
curl -s "$BASE?title=GST" | jq

# Get by id
curl -s $BASE/1 | jq

# Toggle done
curl -s -X PATCH $BASE/1/toggle | jq

# Update
curl -s -X PUT $BASE/1 \
  -H "Content-Type: application/json" \
  -d '{{"title":"File GSTR-3B Q3","dueDate":"2026-01-20","priority":"Critical"}}' | jq

# Delete
curl -s -X DELETE $BASE/2 -w "\\nHTTP %{{http_code}}\\n"

# Request a non-existent item
curl -s $BASE/999 -w "\\nHTTP %{{http_code}}\\n"
# HTTP 404
""", lang="bash")}

<h3>Stretch goals</h3>
{ul([
    "Add a <code>PATCH /api/todos/{id}/priority</code> endpoint that only changes priority.",
    "Add pagination metadata (<code>totalCount</code>, <code>page</code>, <code>pageSize</code>, <code>totalPages</code>) to the GetAll response.",
    "Add a <code>GET /api/todos/due-today</code> that returns items due today.",
    "Support sorting via <code>?sort=dueDate&amp;dir=asc</code> using a switch expression.",
])}
''',
iqs=[("Basic","What is an EF Core migration?","A C# file (and snapshot) generated by <code>dotnet ef migrations add</code> that describes one schema change. <code>MigrateAsync()</code> applies all pending migrations to the database."),
("Basic","Why use DTOs instead of returning the entity directly?","DTOs decouple the API contract from the database model: you can reshape, omit, or rename fields without changing the entity, avoid exposing navigation properties, and prevent over-posting (extra fields being saved)."),
("Intermediate","How does IsDevelopment() change the database provider?","We check <code>app.Environment.IsDevelopment()</code> in Program.cs and register <code>UseSqlite</code> for dev and <code>UseSqlServer</code> for other environments, keeping the development experience simple (file-based, no install) while using SQL Server in production."),
("Intermediate","What does db.Database.MigrateAsync() do at startup?","It applies any pending EF Core migrations to the target database, creating tables if they don't exist. This eliminates the need to run <code>dotnet ef database update</code> manually on each deployment, though for production you may prefer a separate migration step.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Validation, Swagger and Week Review",
"Add endpoint-filter validation, wire up Swashbuckle with XML comments, run a try-to-break table, write the README and push; revise the full week.",
[("Swashbuckle","The popular NuGet package that generates an OpenAPI spec from your ASP.NET Core app and serves Swagger UI."),
("XML documentation comments","Triple-slash comments (<code>/// &lt;summary&gt;</code>) on endpoints/DTOs that Swashbuckle picks up for the OpenAPI spec."),
("Endpoint filter (validation)","A reusable IEndpointFilter that runs data annotation validation on DTOs in minimal API endpoints, since [ApiController] auto-400 is not available."),
("OpenAPI / Swagger UI","A browser interface at <code>/swagger</code> that lets you try every endpoint interactively."),
("HttpContext.RequestServices","Access to the DI container within a filter, useful to resolve validators."),
("ProblemDetails (validation)","Return <code>TypedResults.ValidationProblem(errors)</code> for a 400 with an errors dictionary in the RFC 7807 format."),
("Git workflow","<code>dotnet gitignore</code>, staging migrations, conventional commits for a learning project.")],
["Add <code>&lt;GenerateDocumentationFile&gt;true&lt;/GenerateDocumentationFile&gt;</code> to .csproj for XML comments.",
"Suppress XML warnings for undocumented members with <code>&lt;NoWarn&gt;$(NoWarn);1591&lt;/NoWarn&gt;</code>.",
"The validation endpoint filter pattern validates any DTO annotated with data annotations.",
"<code>AddSwaggerGen()</code> must come before <code>Build()</code>; <code>UseSwagger()</code> must come after."],
f'''
<h3>1. Validation endpoint filter</h3>
{C(r"""
using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Http;

namespace TodoApi.Filters;

// A generic filter that validates any DTO parameter with data annotations
public class ValidateFilter<T> : IEndpointFilter where T : class
{{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext ctx, EndpointFilterDelegate next)
    {{
        // Find the first argument that is of type T
        var dto = ctx.Arguments.OfType<T>().FirstOrDefault();
        if (dto is null) return await next(ctx);

        var results  = new List<ValidationResult>();
        var valid    = Validator.TryValidateObject(dto, new ValidationContext(dto), results, validateAllProperties: true);
        if (!valid)
        {{
            var errors = results
                .GroupBy(r => r.MemberNames.FirstOrDefault() ?? "")
                .ToDictionary(
                    g => g.Key,
                    g => g.Select(r => r.ErrorMessage ?? "Invalid value").ToArray());
            return TypedResults.ValidationProblem(errors);
        }}
        return await next(ctx);
    }}
}}
""", "Filters/ValidateFilter.cs")}
{C(r"""
// Apply to the POST and PUT endpoints in Program.cs:
todos.MapPost("/", TodoEndpoints.Create)
     .AddEndpointFilter<ValidateFilter<CreateTodoDto>>();

todos.MapPut("/{{id:int}}", TodoEndpoints.Update)
     .AddEndpointFilter<ValidateFilter<UpdateTodoDto>>();
""", "Program.cs (excerpt)")}
{C(r"""
# Test: POST with no title
curl -s -X POST http://localhost:5100/api/todos \
  -H "Content-Type: application/json" \
  -d '{{"title":""}}' | jq

# Expected 400 ProblemDetails:
# {{
#   "type": "...",
#   "title": "One or more validation errors occurred.",
#   "status": 400,
#   "errors": {{
#     "Title": ["The Title field is required.", "The field Title must be a string with a maximum length of 200."]
#   }}
# }}
""", lang="bash")}

<h3>2. Swashbuckle / Swagger setup</h3>
{C(r"""
// .csproj additions
// <PropertyGroup>
//   <GenerateDocumentationFile>true</GenerateDocumentationFile>
//   <NoWarn>$(NoWarn);1591</NoWarn>
// </PropertyGroup>
""", lang="xml")}
{C(r"""
// Program.cs — configure Swashbuckle
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(o =>
{{
    o.SwaggerDoc("v1", new() {{ Title = "TodoAPI", Version = "v1",
        Description = "ASP.NET Core 8 minimal API — Week 17 project" }});

    // Pick up XML documentation comments
    var xml = Path.Combine(AppContext.BaseDirectory, $"{{Assembly.GetExecutingAssembly().GetName().Name}}.xml");
    if (File.Exists(xml)) o.IncludeXmlComments(xml);
}});

// ...after builder.Build()...
if (app.Environment.IsDevelopment())
{{
    app.UseSwagger();
    app.UseSwaggerUI(o =>
    {{
        o.SwaggerEndpoint("/swagger/v1/swagger.json", "TodoAPI v1");
        o.RoutePrefix = "swagger";   // http://localhost:5100/swagger
    }});
}}
""", "Program.cs")}
{C(r"""
// Add WithOpenApi() and summary to each endpoint for Swagger
todos.MapGet("/", TodoEndpoints.GetAll)
     .WithSummary("List todos with optional filtering and paging")
     .WithOpenApi();

todos.MapPost("/", TodoEndpoints.Create)
     .WithSummary("Create a new todo item")
     .WithOpenApi()
     .AddEndpointFilter<ValidateFilter<CreateTodoDto>>();
""", "Program.cs (excerpt)")}

<h3>3. Try-to-break table</h3>
{table(["Scenario","Expected behaviour"],[
["POST with empty title","400 ValidationProblem with 'Title is required'"],
["POST with title > 200 chars","400 ValidationProblem with max-length error"],
["GET /api/todos/0 (id = 0 fails :min(1))","404 — route constraint rejects 0"],
["GET /api/todos/abc (non-integer id)","404 — route constraint rejects non-int"],
["PUT /api/todos/999 (non-existent)","404"],
["PATCH /api/todos/999/toggle","404"],
["DELETE /api/todos/1 then GET /api/todos/1","404 — deleted"],
["POST with invalid JSON body","400 — JSON deserialization error"],
["GET /api/todos?priority=InvalidValue","Returns all items (Enum.TryParse returns false → no filter applied)"],
["GET /api/todos?page=0","Returns first page (page gets defaulted to 1 by design; validate if strict)"],
["PATCH /api/todos/1/toggle twice","IsDone toggles back to original value"],
["Concurrent duplicate POST (same title)","Both succeed — no uniqueness constraint on title by design"]])}

<h3>4. README template</h3>
{C(r"""
# TodoApi — Week 17 Project

ASP.NET Core 8 minimal API for managing todo items.
Built as part of the 74-week .NET full-stack roadmap.

## Tech stack
- .NET 8 / ASP.NET Core minimal APIs
- EF Core 8 + SQLite (dev) / SQL Server (prod)
- Swashbuckle / Swagger UI

## Run locally
```bash
dotnet run
# Swagger UI: http://localhost:5100/swagger
```

## Endpoints
| Method | URL                        | Description              |
|--------|----------------------------|--------------------------|
| GET    | /api/todos                 | List (filter, paging)    |
| GET    | /api/todos/{id}            | Get by id                |
| POST   | /api/todos                 | Create                   |
| PUT    | /api/todos/{id}            | Full update              |
| DELETE | /api/todos/{id}            | Delete                   |
| PATCH  | /api/todos/{id}/toggle     | Toggle IsDone            |

## Configuration
| Key                        | Default    | Override             |
|----------------------------|------------|----------------------|
| ConnectionStrings:Default  | todo.db    | env var / user-secret|
| App:MaxPageSize            | 20         | appsettings / env    |
""", lang="text")}

<h3>5. Git setup</h3>
{C(r"""
# From the project root
dotnet new gitignore
git init
git add .
git commit -m "feat: Week 17 TodoApi — minimal API with EF Core, SQLite, Swagger"

# .gitignore already ignores: todo.db, obj/, bin/, .vs/, secrets.json
""", lang="bash")}

<h3>6. Week 17 revision checklist</h3>
<h4>Monday — Pipeline</h4>
{ul(["Program.cs: builder → Build() boundary","Use / Run / Map / MapWhen","Class-based middleware: InvokeAsync, scoped dependencies","Middleware order rules","launchSettings, ASPNETCORE_ENVIRONMENT"])}
<h4>Tuesday — DI</h4>
{ul(["Three lifetimes and their use cases","Captive dependency and ValidateScopes","IServiceScopeFactory for background services","IEnumerable&lt;T&gt; injection","Keyed services (.NET 8)"])}
<h4>Wednesday — Configuration</h4>
{ul(["Config source layering and priorities","__ separator for env vars","User secrets","Options pattern: Configure&lt;T&gt;, ValidateDataAnnotations, ValidateOnStart","IOptions vs IOptionsSnapshot vs IOptionsMonitor"])}
<h4>Thursday — Minimal APIs</h4>
{ul(["Map* verbs, route constraints","Binding sources: route, query, body, header, [AsParameters]","TypedResults vs Results","MapGroup, endpoint filters","ProblemDetails"])}
<h4>Friday — Controllers</h4>
{ul(["[ApiController], auto-400, attribute routing","ActionResult&lt;T&gt; vs IActionResult","CreatedAtAction, ProducesResponseType","Controllers vs Minimal APIs comparison"])}
<h4>Sat/Sun — TodoApi</h4>
{ul(["EF Core + SQLite, migrations, seed","CRUD + toggle + filter/search","Validation endpoint filter","Swashbuckle / Swagger UI","Try-to-break table"])}

<h3>7. Five-question quiz</h3>
<details><summary>Q1. What does this code print?</summary>
{C(r"""
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
int order = 0;
app.Use(async (ctx, next) =>
{{
    Console.Write($"{{++order}}in ");
    await next(ctx);
    Console.Write($"{{order}}out ");
}});
app.Use(async (ctx, next) =>
{{
    Console.Write($"{{++order}}in ");
    await next(ctx);
    Console.Write($"{{order}}out ");
}});
app.Run(async ctx => {{ Console.Write("run "); await ctx.Response.WriteAsync("done"); }});
""")}<b>1in 2in run 3out 3out</b> — each Use increments order on the way in; on the way out order is 3 for both. (Shared variable, not a copy.)</details>

<details><summary>Q2. Does this compile and work correctly?</summary>
{C(r"""
builder.Services.AddSingleton<ReportService>();
// ReportService constructor:
public ReportService(AppDbContext db) {{ }}
""")}<b>It compiles but throws at runtime (or at startup if ValidateScopes is on).</b> AppDbContext is Scoped; injecting it into a Singleton is a captive dependency. The error is: "Cannot consume scoped service 'AppDbContext' from singleton 'ReportService'."</details>

<details><summary>Q3. Which wins — appsettings.json or env var?</summary>
{C(r"""
// appsettings.json: "App": {{ "MaxPageSize": 50 }}
// Environment: App__MaxPageSize=200
Console.WriteLine(config["App:MaxPageSize"]);
""", lang="text")}<b>200</b> — environment variables have higher priority in the default load order.</details>

<details><summary>Q4. What HTTP status does this return for a missing id, and why?</summary>
{C(r"""
app.MapGet("/todos/{{id:int:min(1)}}", async (int id, AppDbContext db) =>
{{
    var item = await db.Todos.FindAsync(id);
    return item is null ? TypedResults.NotFound() : TypedResults.Ok(item);
}});
// Request: GET /todos/0
""")}<b>404</b> — the route constraint <code>:min(1)</code> rejects 0, so the route never matches and ASP.NET Core returns 404 before the handler runs.</details>

<details><summary>Q5. What is the lifetime of a service registered with AddScoped in a minimal API?</summary>
{C(r"""
builder.Services.AddScoped<TodoService>();
app.MapGet("/todos", (TodoService svc) => svc.GetAll());
""")}<b>One instance per HTTP request.</b> When the endpoint handler is invoked, the DI container creates a new TodoService for the request scope and disposes it when the response is sent. Two concurrent requests each get their own instance.</details>

<div class="note tip"><b>Next week:</b> Week 18 — REST API design: resource naming, HTTP semantics, versioning, content negotiation, HATEOAS links, and the product catalog API with controllers.</div>
''',
iqs=[("Basic","What does Swashbuckle do?","Swashbuckle reads your ASP.NET Core app's routing metadata and generates an OpenAPI (Swagger) JSON spec, then serves a Swagger UI at /swagger where you can explore and try every endpoint interactively."),
("Basic","Why do minimal API endpoints need an explicit validation filter while controllers don't?","[ApiController] hooks into the model binding pipeline and returns 400 automatically on invalid ModelState. Minimal APIs don't use controllers, so there's no automatic 400 — you must add it via an IEndpointFilter."),
("Intermediate","How do you apply a filter to every endpoint in a group?","Call <code>group.AddEndpointFilter&lt;TFilter&gt;()</code> on the MapGroup result. The filter runs for every endpoint registered on that group."),
("Intermediate","How does db.Database.MigrateAsync() differ from EnsureCreated()?","MigrateAsync applies all pending EF Core migrations in order, maintaining version history and supporting incremental schema changes. EnsureCreated creates the schema from the current model state in one shot, skipping migrations; it's simpler but cannot evolve the schema over time.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Program.cs and the Middleware Pipeline","Pipeline","Program.cs anatomy, Kestrel, Use/Run/Map, class middleware, middleware order.","2 hrs"),
 (2,"TUE","DI Lifetimes","Lifetimes","Singleton/Scoped/Transient, instance-ID demo, captive dependency, keyed services.","2 hrs"),
 (3,"WED","Configuration and Options","Config &amp; Options","Layering, env vars, user secrets, IOptions vs Snapshot vs Monitor, ValidateOnStart.","2 hrs"),
 (4,"THU","Minimal APIs","Minimal APIs","MapGet/Post/Put/Delete, TypedResults, MapGroup, endpoint filters, ProblemDetails.","2 hrs"),
 (5,"FRI","Controllers","Controllers","[ApiController], attribute routing, auto 400, ActionResult&lt;T&gt;, controllers vs minimal.","2 hrs"),
 (6,"SAT","TodoApi — EF Core CRUD","Project: TodoApi","Minimal API + EF Core, SQLite, DTOs, CRUD + toggle + filter/search, migrations, seed.","4 hrs"),
 (7,"SUN","Validation, Swagger &amp; Review","Review","Validation filter, Swashbuckle, try-to-break, README, quiz, week checklist.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week17.html", 17,
      "Week 17 — ASP.NET Core Fundamentals", "Phase 2", "~18 hrs",
      ["Phase 2 · Week 17 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "To-do API"],
      "ASP.NET Core is the backbone of every .NET web project. This week you will master the middleware pipeline, dependency injection lifetimes, the layered configuration system, and both ways to build HTTP APIs — minimal APIs and controllers. By Sunday you will have a fully working TodoApi with EF Core, Swagger UI, and a validation filter, ready to extend in Week 18.",
      cards, days)
print("built")
