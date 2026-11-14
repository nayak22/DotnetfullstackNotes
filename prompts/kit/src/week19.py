import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Global Exception Handling with IExceptionHandler",
"Handle every unhandled exception in one place: map domain errors to HTTP status codes, return RFC 7807 ProblemDetails, and keep production safe while development stays informative.",
[("IExceptionHandler","ASP.NET Core 8 interface with a single TryHandleAsync method; replaces UseExceptionHandler lambda with a testable, injectable class."),
("ProblemDetails","RFC 7807 JSON error body with type, title, status, detail and extensions; returned by Problem() or typed as ValidationProblemDetails."),
("traceId","A unique string per request (from Activity.Current?.Id) added to ProblemDetails so you can correlate logs with errors reported by users."),
("Chained handlers","Multiple IExceptionHandler implementations registered in order; the first one to return true from TryHandleAsync wins."),
("UseExceptionHandler(\"/error\")","Built-in middleware that invokes the handler chain and falls back to the /error endpoint if nothing handles the exception."),
("AddProblemDetails()","Registers the default ProblemDetails factory and writes Content-Type: application/problem+json."),
("IProblemDetailsService","Injected by AddProblemDetails(); call WriteAsync to serialize and send the response."),
("Domain exception","A business-rule violation that should map to a known HTTP status (e.g. NotFoundException → 404, ConflictException → 409)."),
("Development vs Production","In development, include exception.ToString() in the detail field. In production, log it and return a generic message."),
("ExceptionHandlerMiddleware","The ASP.NET Core middleware that catches unhandled exceptions and invokes IExceptionHandler implementations."),
("StatusCodes.Status422UnprocessableEntity","Returned for domain-rule violations where the payload was valid JSON but breaks a business constraint.")],
["Register IExceptionHandler implementations with <code>services.AddExceptionHandler&lt;T&gt;()</code> in dependency-injection order.",
"Call <code>app.UseExceptionHandler()</code> (no path) in .NET 8 to activate the IExceptionHandler chain.",
"Always add <code>app.UseExceptionHandler()</code> <em>before</em> <code>app.UseRouting()</code> so it catches routing errors too.",
"Return <code>false</code> from TryHandleAsync to let the next handler try; return <code>true</code> to short-circuit.",
"Enrich ProblemDetails with a traceId extension so your support team can find the log entry.",
"Test exception handling with integration tests that deliberately trigger each exception type."],
f'''
<h3>1. Why IExceptionHandler?</h3>
<p>Before .NET 8 teams registered a <code>UseExceptionHandler("/error")</code> endpoint and scattered <code>try/catch</code> blocks across controllers. IExceptionHandler centralises the mapping, keeps it out of business logic, and is properly injectable and testable.</p>
{C(r"""
// Before .NET 8 — scattered catch blocks
[HttpGet("{id}")]
public IActionResult Get(int id)
{
    try { return Ok(_service.FindPost(id)); }
    catch (NotFoundException ex) { return NotFound(ex.Message); }  // repeated everywhere
}

// .NET 8 — declare once in a handler class, controllers throw freely
[HttpGet("{id}")]
public IActionResult Get(int id) => Ok(_service.FindPost(id));  // exceptions flow up
""")}

<h3>2. Domain exception hierarchy</h3>
{C(r"""
// Blog.Core/Exceptions/DomainException.cs
namespace Blog.Core.Exceptions;

public abstract class DomainException : Exception
{
    protected DomainException(string message) : base(message) { }
}

public sealed class NotFoundException     : DomainException
{
    public NotFoundException(string resource, object key)
        : base($"{resource} '{key}' was not found.") { }
}

public sealed class ConflictException     : DomainException
{
    public ConflictException(string message) : base(message) { }
}

public sealed class UnprocessableException : DomainException
{
    public UnprocessableException(string message) : base(message) { }
}
""", "Blog.Core/Exceptions/DomainException.cs")}

<h3>3. Mapping domain exceptions to ProblemDetails</h3>
{C(r"""
// Blog.Api/Exceptions/DomainExceptionHandler.cs
using Blog.Core.Exceptions;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace Blog.Api.Exceptions;

public sealed class DomainExceptionHandler(
    IProblemDetailsService problemDetailsService,
    ILogger<DomainExceptionHandler> logger) : IExceptionHandler
{
    private static readonly Dictionary<Type, int> StatusMap = new()
    {
        [typeof(NotFoundException)]      = StatusCodes.Status404NotFound,
        [typeof(ConflictException)]      = StatusCodes.Status409Conflict,
        [typeof(UnprocessableException)] = StatusCodes.Status422UnprocessableEntity,
    };

    public async ValueTask<bool> TryHandleAsync(
        HttpContext ctx,
        Exception exception,
        CancellationToken ct)
    {
        if (exception is not DomainException domain) return false;  // let the next handler try

        var status = StatusMap.GetValueOrDefault(exception.GetType(), StatusCodes.Status400BadRequest);
        logger.LogWarning(exception, "Domain exception: {Message}", domain.Message);

        ctx.Response.StatusCode = status;

        await problemDetailsService.WriteAsync(new()
        {
            HttpContext = ctx,
            ProblemDetails = new ProblemDetails
            {
                Status  = status,
                Title   = exception.GetType().Name.Replace("Exception", ""),
                Detail  = domain.Message,
                Extensions = { ["traceId"] = System.Diagnostics.Activity.Current?.Id ?? ctx.TraceIdentifier }
            }
        });

        return true;    // handled
    }
}
""", "Blog.Api/Exceptions/DomainExceptionHandler.cs")}

<h3>4. Catch-all handler for unexpected exceptions</h3>
{C(r"""
// Blog.Api/Exceptions/GlobalExceptionHandler.cs
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace Blog.Api.Exceptions;

public sealed class GlobalExceptionHandler(
    IProblemDetailsService problemDetailsService,
    ILogger<GlobalExceptionHandler> logger,
    IHostEnvironment env) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext ctx,
        Exception exception,
        CancellationToken ct)
    {
        logger.LogError(exception, "Unhandled exception on {Method} {Path}",
            ctx.Request.Method, ctx.Request.Path);

        ctx.Response.StatusCode = StatusCodes.Status500InternalServerError;

        // Show full stack trace only in Development
        string detail = env.IsDevelopment()
            ? exception.ToString()
            : "An unexpected error occurred. Contact support with the traceId below.";

        await problemDetailsService.WriteAsync(new()
        {
            HttpContext = ctx,
            ProblemDetails = new ProblemDetails
            {
                Status  = 500,
                Title   = "InternalServerError",
                Detail  = detail,
                Extensions = { ["traceId"] = System.Diagnostics.Activity.Current?.Id ?? ctx.TraceIdentifier }
            }
        });

        return true;
    }
}
""", "Blog.Api/Exceptions/GlobalExceptionHandler.cs")}

<h3>5. Registration in Program.cs</h3>
{C(r"""
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddProblemDetails();                               // must come first
builder.Services.AddExceptionHandler<DomainExceptionHandler>();    // specific → general order
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

var app = builder.Build();

app.UseExceptionHandler();   // .NET 8: no path — activates the IExceptionHandler chain
app.UseHttpsRedirection();
app.MapControllers();

app.Run();
""", "Blog.Api/Program.cs (excerpt)")}
{tip("Order matters: register the most specific handler first. If <code>DomainExceptionHandler</code> returns false, <code>GlobalExceptionHandler</code> handles the remainder.")}
{warn("Never swallow exceptions silently. If you return true from TryHandleAsync the caller sees no error; at minimum log the exception at Error level.")}

<h3>6. What the response looks like</h3>
{C(r"""
// POST /api/posts  with a slug that already exists
// HTTP 409 Conflict
{
  "type":   "https://tools.ietf.org/html/rfc7231#section-6.5.8",
  "title":  "Conflict",
  "status": 409,
  "detail": "A post with slug 'mastering-linq-india' already exists.",
  "traceId": "00-4e7a9c3d1b2f56a8e0b7c4d5e6f7a8b9-01"
}
""", lang="json")}
''',
["Registering <code>UseExceptionHandler()</code> <em>after</em> <code>MapControllers()</code> — it must be first in the pipeline.",
"Forgetting <code>AddProblemDetails()</code> — IProblemDetailsService won't be available.",
"Returning <code>true</code> from TryHandleAsync without writing a response — the client receives 500 with no body.",
"Leaking stack traces in production — always check IHostEnvironment.IsProduction().",
"Throwing raw <code>Exception</code> from service layer — define a domain hierarchy so handlers can distinguish causes."],
("40 min", [
    "Add four domain exceptions (NotFoundException, ConflictException, UnprocessableException, ForbiddenException) to a class library and write DomainExceptionHandler.",
    "Register GlobalExceptionHandler after it and confirm that an unhandled ArithmeticException returns 500 with the traceId.",
    "Write an integration test using WebApplicationFactory that GETs /api/posts/9999 and asserts the response body is application/problem+json with status 404."
]),
[("What does TryHandleAsync returning false mean?","It means this handler declines to handle the exception and ASP.NET Core passes it to the next registered IExceptionHandler."),
("What is the advantage of ProblemDetails over a custom error DTO?","ProblemDetails is an RFC 7807 standard that clients, proxies and monitoring tools already understand. It carries status, title, detail and extensions in a consistent shape."),
("How do you stop stack traces appearing in production?","Inject IHostEnvironment and check env.IsProduction(); only include exception.ToString() in the detail field for Development environments.")],
[("Basic","What is IExceptionHandler in ASP.NET Core 8?","An interface with TryHandleAsync that lets you map exceptions to HTTP responses in a testable, DI-friendly class. Multiple handlers are chained; the first to return true wins."),
("Basic","What HTTP status should a NotFoundException return and why?","404 Not Found, because the requested resource genuinely does not exist. Using 500 for a missing record makes it impossible for callers to distinguish application bugs from missing data."),
("Basic","What is ProblemDetails?","An RFC 7807 JSON object with type, title, status and detail fields that standardises error responses across HTTP APIs. ASP.NET Core's AddProblemDetails() wires it up automatically."),
("Intermediate","How do you chain exception handlers in .NET 8?","Register them in DI order with services.AddExceptionHandler&lt;T&gt;(). Call app.UseExceptionHandler() (no path). The middleware invokes each in registration order until one returns true."),
("Intermediate","How do you correlate an error report from a user to a log entry?","Add Activity.Current?.Id (the distributed trace ID) to ProblemDetails.Extensions[\"traceId\"]. The same ID appears in Serilog's structured logs via the enricher, so a support engineer can filter by it in Seq or Application Insights."),
("Intermediate","What is the difference between UseExceptionHandler(\"/error\") and UseExceptionHandler() (no path) in .NET 8?","The path variant re-executes the pipeline to an error endpoint, requiring a controller action. The no-path variant (new in .NET 8) calls the IExceptionHandler chain directly without a re-execution, which is simpler and doesn't expose an extra route.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Structured Logging with Serilog",
"Replace the default ILogger with Serilog's structured pipeline: two-stage bootstrap, appsettings-driven sinks, enrichers, and request logging middleware for every HTTP call.",
[("Serilog","A structured logging library for .NET; writes log events as key-value property bags rather than interpolated strings."),
("Sink","A destination for log events: Console, File, Seq, Application Insights, Elasticsearch, etc."),
("Two-stage bootstrap","Starting Serilog from code (Log.Logger) before the host is built, so startup errors are caught; then reconfiguring from appsettings.json once DI is ready."),
("Message template","A string with named holes like <code>{UserId}</code> that Serilog captures as structured properties, not raw string interpolation."),
("Enricher","A component that attaches extra properties to every log event: machine name, environment, thread ID, correlation ID."),
("Seq","A self-hosted log server that understands Serilog's structured format; great for development because you can filter by any property."),
("UseSerilogRequestLogging","Serilog middleware that logs one structured line per HTTP request, replacing the noisy built-in Microsoft HTTP logs."),
("Level override","Silencing verbose Microsoft.* or EF Core SQL logs by setting their minimum level higher than the global minimum."),
("Destructuring","<code>@</code> prefix in a template: <code>{@User}</code> captures all object properties, not just ToString()"),
("Log.Fatal + Log.CloseAndFlush","Flush sinks synchronously before the process exits so the last log entries reach sinks, especially async file sinks."),
("LogContext.PushProperty","Pushes a property into all subsequent log events within a using block (e.g. the request's tenant ID).")],
["Use message templates with named holes, never string interpolation — it destroys the structure that makes filtering fast.",
"Always call <code>Log.CloseAndFlush()</code> in a try/catch/finally around <code>host.Run()</code> so final entries reach sinks on crashes.",
"Level overrides in appsettings.json silence <code>Microsoft.EntityFrameworkCore.*</code> and <code>Microsoft.AspNetCore.*</code> without changing the global level.",
"UseSerilogRequestLogging must come before UseRouting and UseAuthorization to capture the status code.",
"<code>{:l}</code> after a hole logs without quotes; use it for single-word string properties in concise output templates.",
"Seq binds to localhost:5341 by default; run it with Docker for local development."],
f'''
<h3>1. Install and two-stage bootstrap</h3>
{C(r"""
dotnet add package Serilog.AspNetCore          # pulls in Serilog + ASP.NET Core integration
dotnet add package Serilog.Sinks.Seq           # Seq sink
dotnet add package Serilog.Sinks.File          # rolling file sink
dotnet add package Serilog.Enrichers.Environment
dotnet add package Serilog.Enrichers.Thread
""", lang="bash")}
{C(r"""
// Blog.Api/Program.cs
using Serilog;

// Stage 1: minimal bootstrap logger to catch startup errors
Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Warning()                // quiet for startup
    .WriteTo.Console(outputTemplate:
        "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj}{NewLine}{Exception}")
    .CreateBootstrapLogger();

try
{
    var builder = WebApplication.CreateBuilder(args);

    // Stage 2: replace with the full configuration from appsettings.json + DI
    builder.Host.UseSerilog((ctx, services, cfg) =>
        cfg.ReadFrom.Configuration(ctx.Configuration)
           .ReadFrom.Services(services)         // allows enrichers registered as services
           .Enrich.FromLogContext()              // picks up LogContext.PushProperty
           .Enrich.WithMachineName()
           .Enrich.WithEnvironmentName());

    // ... services and middleware

    var app = builder.Build();
    app.UseSerilogRequestLogging(opts =>         // ONE structured line per request
    {
        opts.MessageTemplate =
            "HTTP {RequestMethod} {RequestPath} → {StatusCode} in {Elapsed:0.0}ms";
        opts.EnrichDiagnosticContext = (diag, ctx) =>
        {
            diag.Set("ClientIp", ctx.Connection.RemoteIpAddress);
            diag.Set("UserAgent", ctx.Request.Headers.UserAgent.FirstOrDefault());
        };
    });
    app.UseExceptionHandler();
    app.UseRouting();
    app.MapControllers();
    app.Run();
}
catch (Exception ex) when (ex is not HostAbortedException)
{
    Log.Fatal(ex, "Application startup failed");
}
finally
{
    Log.CloseAndFlush();    // ensures async sinks (File, Seq) write their buffers
}
""", "Blog.Api/Program.cs")}

<h3>2. appsettings.json configuration</h3>
{C(r"""
{
  "Serilog": {
    "Using": [ "Serilog.Sinks.Console", "Serilog.Sinks.File", "Serilog.Sinks.Seq" ],
    "MinimumLevel": {
      "Default": "Information",
      "Override": {
        "Microsoft":                                 "Warning",
        "Microsoft.Hosting.Lifetime":                "Information",
        "Microsoft.EntityFrameworkCore.Database.Command": "Warning"
      }
    },
    "WriteTo": [
      {
        "Name": "Console",
        "Args": {
          "outputTemplate": "[{Timestamp:HH:mm:ss} {Level:u3}] {SourceContext}: {Message:lj}{NewLine}{Exception}"
        }
      },
      {
        "Name": "File",
        "Args": {
          "path": "logs/blog-.log",
          "rollingInterval": "Day",
          "retainedFileCountLimit": 14,
          "outputTemplate": "{Timestamp:yyyy-MM-dd HH:mm:ss.fff} [{Level:u3}] {SourceContext} {Message:lj}{NewLine}{Exception}"
        }
      },
      {
        "Name": "Seq",
        "Args": { "serverUrl": "http://localhost:5341" }
      }
    ],
    "Enrich": [ "FromLogContext", "WithMachineName", "WithEnvironmentName", "WithThreadId" ],
    "Properties": { "Application": "BlogApi" }
  }
}
""", "appsettings.json (Serilog section)", lang="json")}
{warn("Never use string interpolation in log calls: <code>_logger.LogInformation($\"User {{Id}} logged in\", id)</code> loses structure. The correct form is <code>_logger.LogInformation(\"User {Id} logged in\", id)</code>.")}

<h3>3. Using ILogger in a controller and service</h3>
{C(r"""
// Blog.Api/Controllers/PostsController.cs
[ApiController]
[Route("api/[controller]")]
public class PostsController(IPostService service, ILogger<PostsController> logger) : ControllerBase
{
    [HttpGet("{slug}")]
    public async Task<IActionResult> GetBySlug(string slug, CancellationToken ct)
    {
        // Message template — structured; slug is captured as a property
        logger.LogInformation("Fetching post {Slug}", slug);

        var post = await service.GetBySlugAsync(slug, ct);
        return Ok(post);
    }

    [HttpPost]
    public async Task<IActionResult> Create(CreatePostRequest req, CancellationToken ct)
    {
        // Destructuring with @ captures all PostRequest fields
        logger.LogInformation("Creating post {@Request}", req);
        var post = await service.CreateAsync(req, ct);
        logger.LogInformation("Post {PostId} created for author {AuthorId}", post.Id, post.AuthorId);
        return CreatedAtAction(nameof(GetBySlug), new { slug = post.Slug }, post);
    }
}
""", "Blog.Api/Controllers/PostsController.cs")}

<h3>4. Pushing contextual properties with LogContext</h3>
{C(r"""
// Blog.Api/Middleware/TenantLoggingMiddleware.cs
// Adds TenantId to every log event within the request
public class TenantLoggingMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(HttpContext ctx)
    {
        var tenantId = ctx.Request.Headers["X-Tenant-Id"].FirstOrDefault() ?? "default";

        using (LogContext.PushProperty("TenantId", tenantId))
        using (LogContext.PushProperty("UserId", ctx.User.FindFirst("sub")?.Value))
        {
            await next(ctx);
        }
    }
}

// In Program.cs:
app.UseMiddleware<TenantLoggingMiddleware>();
""")}
{tip("Run Seq with Docker for a great local experience: <code>docker run --rm -p 5341:5341 -p 5342:80 datalust/seq:latest</code> then browse http://localhost:5342.")}

<h3>5. Seq sink in action — filtering structured logs</h3>
{C(r"""
// In Seq's web UI you can filter by any property:
//
// StatusCode = 500                      (find server errors)
// Slug = "mastering-linq-india"         (trace one post)
// @Level = "Warning" and AuthorId = 42 (warnings for one author)
// Elapsed > 500                         (slow requests)
//
// All possible because {Slug}, {StatusCode}, {AuthorId} etc. are stored
// as properties, not embedded in a message string.
""", lang="text")}
''',
["Using <code>_logger.LogInformation($\"Found {{Id}}: {{Name}}\", id, name)</code> — the $ makes it a plain string; drop the $ and let Serilog do the templating.",
"Forgetting <code>Log.CloseAndFlush()</code> — async file/Seq sinks drop the last few events on shutdown.",
"Calling <code>UseSerilogRequestLogging</code> after <code>UseRouting</code> — it won't see the matched endpoint.",
"Not overriding Microsoft.* log levels — the console floods with framework noise at Information.",
"Using <code>{@LargeObject}</code> destructuring on a 100-field EF entity — it logs every property; select only what you need."],
("40 min", [
    "Add Serilog to the BlogApi with the Console and rolling-File sinks; confirm that a request to GET /api/posts writes one structured line from UseSerilogRequestLogging.",
    "Start Seq via Docker and add the Seq sink; observe the TenantId property appearing on every request log.",
    "Override <code>Microsoft.EntityFrameworkCore.Database.Command</code> to Warning so SQL queries are silenced, then set it to Debug and confirm EF's SQL appears in the Seq stream."
]),
[("What is a Serilog message template?","A string with named holes like {OrderId} that Serilog captures as structured key-value properties, stored separately from the message text so you can filter and search on them."),
("Why call Log.CloseAndFlush() on shutdown?","Serilog sinks are often asynchronous; without an explicit flush the last buffered events may never reach the sink, losing logs on crashes."),
("What does UseSerilogRequestLogging replace?","Microsoft.AspNetCore.Hosting.Internal.WebHost's built-in request logging, which emits two verbose lines per request. Serilog replaces them with one structured line containing method, path, status code and elapsed time.")],
[("Basic","Why prefer Serilog message templates over string interpolation?","Templates keep properties as typed values in the log event. Serilog and sinks like Seq index and filter on them directly. Interpolation collapses everything into a string, losing queryability."),
("Basic","What is the two-stage bootstrap pattern?","A minimal Log.Logger is built before the host so startup exceptions are captured. Once DI is configured, Host.UseSerilog() replaces it with the full configuration from appsettings.json and registered services."),
("Basic","What does UseSerilogRequestLogging add?","One structured log event per request with method, path, status code and elapsed milliseconds. It enriches the event with endpoint information and replaces the noisier built-in Microsoft HTTP logging."),
("Intermediate","What is a Serilog enricher?","An enricher attaches extra properties to every log event: machine name, environment, thread ID, correlation ID. Enrichers are registered in the LoggerConfiguration and run for every event written to any sink."),
("Intermediate","How do you silence EF Core's SQL query logs without changing the global minimum level?","Add an override in appsettings.json Serilog.MinimumLevel.Override: set Microsoft.EntityFrameworkCore.Database.Command to Warning (or higher). The logger for that namespace uses Warning as its threshold, while everything else stays at Information."),
("Intermediate","How does LogContext.PushProperty work?","It pushes a named property into the ambient log context for the duration of a using block. Any log events written inside that scope (including those in called services) automatically carry the property. The scope is AsyncLocal, so it flows correctly across awaits.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Health Checks and CORS",
"Expose liveness and readiness endpoints that orchestrators can poll, write a custom DbContext health check, and configure CORS policies that allow the right origins without opening the API to everyone.",
[("Health check","An endpoint that reports whether the application is Healthy, Degraded or Unhealthy, used by Kubernetes, Azure Load Balancer, or a monitoring dashboard."),
("Liveness","Probe: is the process alive? Return Healthy unless the app is deadlocked or needs a restart."),
("Readiness","Probe: can the app serve traffic? Return Unhealthy while warming up, running migrations or when a dependency (DB, Redis) is unreachable."),
("IHealthCheck","Interface with a single CheckHealthAsync method; return HealthCheckResult.Healthy/Degraded/Unhealthy."),
("HealthCheckContext","Passed to CheckHealthAsync; holds the registration (name, tags, failure status)."),
("AddDbContextCheck&lt;T&gt;","Extension from Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore; pings the DB with a lightweight query."),
("HealthCheckOptions","Configures the /health response: response writer, predicate to filter by tag, result status codes."),
("CORS","Cross-Origin Resource Sharing: browser policy that blocks JS on origin A from calling an API on origin B unless B sends the right headers."),
("AllowedOrigins","The specific scheme+host+port combos a policy permits, e.g. https://blogfront.example.com."),
("Preflight","An HTTP OPTIONS request the browser sends before a cross-origin non-simple request; the API must reply with Access-Control headers."),
("Named policy","A CORS policy registered with AddCors and applied by name, allowing different rules for different endpoint groups."),
("Credentials pitfall","You cannot combine AllowAnyOrigin() with AllowCredentials() — the browser refuses; always specify exact origins for credentialled requests.")],
["Use tags (\"live\", \"ready\") to route Kubernetes liveness and readiness probes to separate endpoints.",
"Return Degraded (not Unhealthy) when a non-critical dependency is slow; orchestrators restart the pod on Unhealthy.",
"Never call <code>AllowAnyOrigin().AllowCredentials()</code> — it throws at startup since .NET 5.",
"Put CORS before UseRouting (or at minimum before UseAuthorization) to ensure preflight OPTIONS requests are handled.",
"Use <code>RequireCors(\"policy\")</code> per endpoint, or <code>app.MapControllers().RequireCors(\"policy\")</code> globally.",
"Return health check results within 10 seconds; set a timeout on slow DB checks with cts.CancelAfter()."],
f'''
<h3>1. Liveness and readiness with built-in checks</h3>
{C(r"""
// Blog.Api/Program.cs — health check registration
builder.Services.AddHealthChecks()
    .AddDbContextCheck<BlogDbContext>(
        name:          "database",
        failureStatus: HealthStatus.Unhealthy,
        tags:          ["ready"])                     // only on the readiness endpoint
    .AddCheck<SlugCacheHealthCheck>(
        name:          "slug-cache",
        failureStatus: HealthStatus.Degraded,
        tags:          ["ready"]);                    // non-critical: Degraded, not Unhealthy

// Map two separate endpoints
app.MapHealthChecks("/health/live",  new HealthCheckOptions
{
    // Liveness: only the checks tagged "live" (or no tag filter = process is up)
    Predicate = _ => false,                           // skip all checks; just return Healthy
    ResponseWriter = UIResponseWriter.WriteHealthCheckUIResponse
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready"),
    ResponseWriter = UIResponseWriter.WriteHealthCheckUIResponse
});
""", "Blog.Api/Program.cs (health checks)")}
{tip("Add the <code>AspNetCore.HealthChecks.UI.Client</code> NuGet package for the richer JSON format; the basic checks work without it.")}

<h3>2. Custom IHealthCheck — checking the EF Core DB</h3>
{C(r"""
// Blog.Api/HealthChecks/DatabaseHealthCheck.cs
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace Blog.Api.HealthChecks;

public sealed class DatabaseHealthCheck(BlogDbContext db) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken ct = default)
    {
        try
        {
            // Lightweight: just runs "SELECT 1" via CanConnectAsync
            bool canConnect = await db.Database.CanConnectAsync(ct);

            if (!canConnect)
                return HealthCheckResult.Unhealthy("Cannot connect to SQL Server.");

            // Check post count as a quick sanity test
            int count = await db.Posts.CountAsync(ct);
            return HealthCheckResult.Healthy($"DB reachable. Posts: {count}.");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("DB check threw.", ex);
        }
    }
}
""", "Blog.Api/HealthChecks/DatabaseHealthCheck.cs")}

<h3>3. Health check response format</h3>
{C(r"""
// GET /health/ready
{
  "status": "Healthy",
  "totalDuration": "00:00:00.0423117",
  "entries": {
    "database": {
      "data":     {},
      "description": "DB reachable. Posts: 42.",
      "duration": "00:00:00.0391043",
      "status":   "Healthy",
      "tags":     ["ready"]
    },
    "slug-cache": {
      "data":     {},
      "status":   "Healthy",
      "tags":     ["ready"]
    }
  }
}
""", lang="json")}

<h3>4. CORS — named policies</h3>
{C(r"""
// Blog.Api/Program.cs — CORS registration
const string FrontendPolicy = "AllowBlogFrontend";
const string PublicApiPolicy = "AllowAll";

builder.Services.AddCors(opts =>
{
    opts.AddPolicy(FrontendPolicy, policy =>
        policy.WithOrigins(
                "https://blog.example.in",
                "https://dev.blog.example.in",
                "http://localhost:3000")          // local React dev server
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials()                 // cookies / auth headers
              .SetPreflightMaxAge(TimeSpan.FromHours(1)));

    opts.AddPolicy(PublicApiPolicy, policy =>
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .WithMethods("GET")                 // read-only public endpoints
              .SetPreflightMaxAge(TimeSpan.FromHours(1)));
              // ⚠ AllowAnyOrigin means NO AllowCredentials — that would throw
});

// Apply policies in the pipeline
app.UseCors();         // must be before UseRouting for minimal API; for controllers either order works
app.UseRouting();
app.UseAuthorization();

// Controller-level: attribute
// [EnableCors(FrontendPolicy)]
// or on the route group at mapping:
app.MapControllers().RequireCors(FrontendPolicy);
""", "Blog.Api/Program.cs (CORS)")}
{warn("Combining <code>AllowAnyOrigin()</code> with <code>AllowCredentials()</code> throws <code>InvalidOperationException</code> at app.Build() since .NET 5. For credentialled requests always enumerate exact origins.")}

<h3>5. CORS in action — preflight</h3>
{C(r"""
// Browser sends (automatically, before the real POST):
OPTIONS /api/posts HTTP/1.1
Origin: https://blog.example.in
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type, Authorization

// ASP.NET Core replies (if the request origin matches the policy):
HTTP/1.1 204 No Content
Access-Control-Allow-Origin:  https://blog.example.in
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, ...
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 3600
Vary: Origin
""", lang="text")}
{table(["Scenario","Use"],[
["Public read-only API (CDN-served)","AllowAnyOrigin + WithMethods(GET)"],
["SPA hitting a backend it owns","WithOrigins(exact list) + AllowCredentials"],
["Dev: local SPA + local API","WithOrigins(localhost:3000, localhost:5173)"],
["Multi-tenant SaaS","Read the allowed origins from appsettings per tenant at startup"]])}
''',
["Putting health check endpoints inside the authenticated route group — monitoring agents can't reach them.",
"Using <code>AllowAnyOrigin</code> for a production API that sets cookies (browsers will block it).",
"Not tagging checks — without tags you can't split liveness from readiness probes.",
"Registering <code>AddHealthChecks()</code> but not calling <code>app.MapHealthChecks(\"/health\")</code> — the endpoint never exists.",
"Forgetting <code>app.UseCors()</code> — CORS policies are registered but never applied."],
("40 min", [
    "Register a DatabaseHealthCheck and a custom MemoryHealthCheck (flag as Degraded when GC total memory &gt; 200 MB). Map them to /health/live (memory only) and /health/ready (db + memory).",
    "Add a 'BlogFrontend' CORS policy that allows http://localhost:3000 and use curl to send an OPTIONS preflight and confirm the Access-Control-Allow-Origin header.",
    "Intentionally break the DB connection string and confirm /health/ready returns 503 while /health/live returns 200."
]),
[("What is the difference between liveness and readiness?","Liveness checks whether the process is alive and should restart. Readiness checks whether the process is ready to serve traffic — a pod can be alive but not ready if the DB is unavailable."),
("Why can't you use AllowAnyOrigin with AllowCredentials?","The CORS specification forbids the wildcard origin (*) with credentials because it would allow any website to send authenticated requests. Browsers block it, and ASP.NET Core throws at startup."),
("What HTTP method does a CORS preflight use?","OPTIONS. The browser sends OPTIONS before a non-simple cross-origin request; the server must respond with the allowed-origin, methods, and headers headers, with no body.")],
[("Basic","What does AddDbContextCheck do?","It registers a health check that calls db.Database.CanConnectAsync() — essentially sending SELECT 1 to SQL Server — and returns Healthy if it succeeds, or Unhealthy/Degraded depending on the configured failureStatus."),
("Basic","What is a named CORS policy?","A CORS configuration registered with a string name in AddCors. You can apply different policies to different endpoints — a permissive public-read policy on /api/feed and a strict credentialled policy on /api/admin — rather than a single global rule."),
("Basic","What tags are conventionally used for Kubernetes health checks?","'live' for liveness probes and 'ready' for readiness probes. Kubernetes calls /health/live every few seconds to decide whether to restart the pod, and /health/ready to decide whether to route traffic to it."),
("Intermediate","How do you prevent unauthenticated access to the /health endpoint in production?","Two options: (1) filter at the network level (only allow the load balancer IP), or (2) add .RequireAuthorization() with an AllowAnonymous exception for health checks. Many teams exclude the /health path at the reverse proxy level."),
("Intermediate","What is the Vary: Origin header and why does ASP.NET Core add it?","It tells CDNs and proxies that the response content varies by the Origin header, so they cache separate responses for each origin rather than serving cached CORS headers intended for one origin to a different origin."),
("Intermediate","How does SetPreflightMaxAge work?","It sets Access-Control-Max-Age, instructing the browser to cache the preflight response for that many seconds and skip sending OPTIONS for repeat requests in that window. Reduces preflight overhead for high-traffic APIs.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Rate Limiting and Output Caching",
"Protect your API from abuse with .NET 8's built-in rate limiters and speed it up with OutputCache policies that support tag-based eviction — no extra infrastructure required.",
[("AddRateLimiter","ASP.NET Core 8 service registration that enables the rate-limiting middleware and policies."),
("FixedWindowLimiter","Allows N requests per fixed time window (e.g. 10 req / 60 sec); resets at the window boundary."),
("SlidingWindowLimiter","Allows N requests per rolling window divided into segments; smoother than fixed window."),
("TokenBucketLimiter","Tokens replenish at a fixed rate; allows bursts up to the bucket size."),
("ConcurrencyLimiter","Caps the number of requests processed at the same time regardless of time."),
("PartitionedRateLimiter","A rate limiter keyed by a partition (e.g. user ID, IP address) so each user gets their own bucket."),
("429 Too Many Requests","The HTTP status code returned when a request is rejected by the rate limiter."),
("Retry-After","Response header telling the client how many seconds to wait before retrying."),
("OutputCache","ASP.NET Core 7+ middleware that caches full HTTP responses in-process (or Redis in .NET 8+)."),
("Cache policy","Named configuration for OutputCache: duration, vary-by headers/query, tags."),
("Tag eviction","Calling OutputCacheStore.EvictByTagAsync(\"tag\") removes all cached responses labelled with that tag."),
("ResponseCaching","Older middleware that respects Cache-Control headers; less control, no server-side eviction.")],
["Use PartitionedRateLimiter keyed by user ID in authenticated APIs to give each user their own quota.",
"On rejection, write Retry-After in OnRejected so clients back off correctly.",
"OutputCache stores the full response body; only cache idempotent GET/HEAD endpoints.",
"Add a tag to every cached endpoint in a resource group; on write, evict by that tag to invalidate the whole group.",
"ResponseCaching is controlled by Cache-Control headers from the client — OutputCache is controlled by the server, making it more secure.",
"Set a short base duration (e.g. 60 s) and vary by query string or user claim for personalised content."],
f'''
<h3>1. Registering rate limit policies</h3>
{C(r"""
// Blog.Api/Program.cs
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

builder.Services.AddRateLimiter(opts =>
{
    // --- Global fixed-window policy ---
    opts.AddFixedWindowLimiter("global", o =>
    {
        o.PermitLimit         = 100;
        o.Window              = TimeSpan.FromMinutes(1);
        o.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
        o.QueueLimit          = 10;
    });

    // --- Per-user sliding window (authenticated endpoint) ---
    opts.AddPolicy("perUser", httpCtx =>
        RateLimitPartition.GetSlidingWindowLimiter(
            partitionKey: httpCtx.User.FindFirst("sub")?.Value ?? "anon",
            factory: _ => new SlidingWindowRateLimiterOptions
            {
                PermitLimit    = 20,
                Window         = TimeSpan.FromMinutes(1),
                SegmentsPerWindow = 4,
                QueueLimit     = 0,
            }));

    // --- Token bucket for comment creation ---
    opts.AddTokenBucketLimiter("commentCreate", o =>
    {
        o.TokenLimit           = 5;
        o.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
        o.QueueLimit           = 0;
        o.ReplenishmentPeriod  = TimeSpan.FromMinutes(1);
        o.TokensPerPeriod      = 2;
        o.AutoReplenishment    = true;
    });

    // 429 response with Retry-After header
    opts.OnRejected = async (ctx, ct) =>
    {
        ctx.HttpContext.Response.StatusCode = StatusCodes.Status429TooManyRequests;

        if (ctx.Lease.TryGetMetadata(MetadataName.RetryAfter, out var retryAfter))
            ctx.HttpContext.Response.Headers.RetryAfter =
                ((int)retryAfter.TotalSeconds).ToString();

        await ctx.HttpContext.Response.WriteAsync(
            "Too many requests. Please try again later.", ct);
    };
});
""", "Blog.Api/Program.cs (rate limiting)")}

<h3>2. Applying policies to endpoints</h3>
{C(r"""
// In Program.cs middleware order:
app.UseRateLimiter();     // before UseRouting for best coverage

// Controller-level attribute:
[EnableRateLimiting("commentCreate")]
[HttpPost("{postId}/comments")]
public async Task<IActionResult> AddComment(int postId, CreateCommentRequest req, CancellationToken ct)
{
    var comment = await _commentService.CreateAsync(postId, req, ct);
    return CreatedAtAction(null, new { id = comment.Id }, comment);
}

// Or on a minimal-API route:
app.MapGet("/api/posts/{slug}", handler)
   .RequireRateLimiting("global");
""")}
{tip("Use <code>[DisableRateLimiting]</code> on health-check and internal endpoints so monitoring agents are never throttled.")}

<h3>3. OutputCache policies</h3>
{C(r"""
builder.Services.AddOutputCache(opts =>
{
    // Base policy: cache GET responses for 60 seconds
    opts.AddBasePolicy(b => b.Expire(TimeSpan.FromSeconds(60)));

    // Post-list policy: 2 min, vary by page/pageSize query params, tagged "posts"
    opts.AddPolicy("postList", b =>
        b.Expire(TimeSpan.FromMinutes(2))
         .SetVaryByQuery("page", "pageSize", "tag")
         .Tag("posts"));

    // Single post: 5 min, vary by route slug, tagged "posts" and "post-{slug}"
    opts.AddPolicy("singlePost", b =>
        b.Expire(TimeSpan.FromMinutes(5))
         .SetVaryByRouteValue("slug")
         .Tag("posts"));

    // No cache for admin writes
    opts.AddPolicy("noCache", b => b.NoStore());
});
""", "Blog.Api/Program.cs (output cache)")}

<h3>4. Applying OutputCache and evicting on write</h3>
{C(r"""
// Blog.Api/Controllers/PostsController.cs
[OutputCache(PolicyName = "postList")]
[HttpGet]
public async Task<IActionResult> GetPosts([FromQuery] int page = 1, [FromQuery] int pageSize = 10, CancellationToken ct = default)
{
    var result = await _service.ListAsync(page, pageSize, ct);
    return Ok(result);
}

[OutputCache(PolicyName = "singlePost")]
[HttpGet("{slug}")]
public async Task<IActionResult> GetBySlug(string slug, CancellationToken ct)
{
    var post = await _service.GetBySlugAsync(slug, ct);
    return Ok(post);
}

// On POST / PUT / DELETE — evict the "posts" tag so stale responses are removed
[OutputCache(PolicyName = "noCache")]
[HttpPost]
public async Task<IActionResult> Create(
    CreatePostRequest req,
    [FromServices] IOutputCacheStore cacheStore,
    CancellationToken ct)
{
    var post = await _service.CreateAsync(req, ct);
    await cacheStore.EvictByTagAsync("posts", ct);       // invalidates all cached post responses
    return CreatedAtAction(nameof(GetBySlug), new { slug = post.Slug }, post);
}
""", "Blog.Api/Controllers/PostsController.cs")}

<h3>5. ResponseCaching vs OutputCache comparison</h3>
{table(["","ResponseCaching","OutputCache (.NET 7+)"],[
["Control","Cache-Control headers (client + server)","Server-side policies only"],
["Store","In-process only","In-process or distributed (Redis in .NET 8)"],
["Tag eviction","Not supported","EvictByTagAsync()"],
["Vary by route","Not supported","SetVaryByRouteValue()"],
["Authorization bypass","Cache bypassed if Authorize is present","Explicit NoStore needed"],
["Recommended for","Public pages respecting CDN headers","API responses needing server control"]])}
''',
["Caching POST responses with OutputCache — the middleware only caches GET/HEAD by default; apply <code>NoStore</code> policy on write endpoints.",
"Using FixedWindow for comment creation — it allows bursts at the window boundary; prefer TokenBucket for smooth rate control.",
"Forgetting <code>app.UseRateLimiter()</code> — policies are registered but never enforced.",
"Not evicting cache on writes — stale data served until the policy duration expires.",
"Partitioning by IP address without null checks — a null partition key throws NullReferenceException in the limiter factory."],
("40 min", [
    "Add a fixed-window policy (50 req / min) globally and a token-bucket policy (5 tokens, 2 per minute) on POST /api/posts/{id}/comments. Use curl in a loop to trigger the 429.",
    "Add an OutputCache policy on GET /api/posts with a 2-minute expiry, vary by page and tag query params, and the 'posts' tag. Confirm the response includes X-Cache hit headers on the second request.",
    "On POST /api/posts call EvictByTagAsync('posts') and confirm the subsequent GET returns fresh data (no cache hit)."
]),
[("What is the difference between FixedWindow and SlidingWindow rate limiters?","FixedWindow resets the counter at a fixed boundary (e.g. every 60 s exactly), allowing a burst at the reset point. SlidingWindow tracks a rolling period in segments, distributing the limit more evenly."),
("What does EvictByTagAsync do?","It removes all cached response entries that were tagged with the given string from the OutputCache store, forcing subsequent requests to hit the origin."),
("Why is OutputCache better than ResponseCaching for most APIs?","OutputCache runs server-side logic regardless of Cache-Control headers sent by clients, supports tag eviction and vary-by-route-value, and in .NET 8 can use a distributed store like Redis.")],
[("Basic","What HTTP status code does the rate limiter return on rejection?","429 Too Many Requests. The response should include a Retry-After header indicating how many seconds to wait."),
("Basic","What is a partitioned rate limiter?","A rate limiter that creates a separate bucket per partition key — typically the authenticated user ID or IP address — so each user has an independent quota rather than sharing one global counter."),
("Basic","What is tag-based eviction in OutputCache?","Tagging a cached response with a string and later calling EvictByTagAsync on that string removes all responses with that tag. Useful for invalidating all posts on a create/update without knowing the exact cache keys."),
("Intermediate","When would you choose TokenBucket over FixedWindow?","TokenBucket is better when you want to allow short bursts (up to the bucket size) but limit the sustained rate. FixedWindow can be gamed by sending all requests just before and just after the reset boundary; TokenBucket naturally prevents this."),
("Intermediate","What is the difference between OutputCache and a distributed cache like Redis used manually?","OutputCache is response-level: it stores and serves the full HTTP response transparently with no code changes in controllers. Manual Redis caching is data-level: you cache DTOs or query results and still run controller logic. OutputCache is simpler; manual caching gives more granular control."),
("Intermediate","How does SetVaryByQuery work in an OutputCache policy?","It creates a separate cache entry for each distinct combination of the specified query parameter values. GET /api/posts?page=1&pageSize=10 and GET /api/posts?page=2&pageSize=10 are stored and served independently.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "File Upload and Download",
"Accept IFormFile uploads safely (size limits, content-type whitelist, magic bytes), store files outside wwwroot, and serve them with range-request support.",
[("IFormFile","ASP.NET Core's abstraction for an uploaded file; exposes FileName, ContentType, Length, OpenReadStream()."),
("ContentType whitelist","Checking IFormFile.ContentType against allowed MIME types; necessary but not sufficient — always verify magic bytes too."),
("Magic bytes","The first few bytes of a file that identify its real format, regardless of the file name or declared Content-Type."),
("Safe file name","A server-generated GUID (or slug + GUID) used as the stored name; never trust IFormFile.FileName from the client."),
("wwwroot","The static-file root served directly by the web server; uploaded files should NOT be stored here to prevent direct execution."),
("PhysicalFile","An ActionResult that streams a file from a physical path, setting Content-Type and Content-Disposition headers."),
("VirtualFileResult","Streams from the web root; not suitable for files outside wwwroot."),
("Range request","HTTP Range header support for resumable downloads; FileStreamResult and PhysicalFile handle this automatically."),
("IFormFile.OpenReadStream","Returns a stream you can read and copy without loading the whole file into memory."),
("Antiforgery","For browser form uploads, include a CSRF token; pure JSON/REST APIs use the Authorization header instead, so antiforgery is typically skipped."),
("MaxRequestBodySize","Kestrel and IIS limit the HTTP request body; set it per endpoint to override the default 30 MB.")],
["Never trust <code>IFormFile.FileName</code> or <code>IFormFile.ContentType</code> from the client — they're user-controlled strings.",
"Check magic bytes by opening the stream and reading the first 4–16 bytes before saving.",
"Store uploaded files in a folder outside the content root (e.g. /data/uploads) and serve via a controller, not static files.",
"Use <code>Path.GetRandomFileName()</code> or <code>Guid.NewGuid()</code> for the stored file name; keep the original name in a database column.",
"Stream large files directly to disk with <code>CopyToAsync</code>; don't buffer them in memory with <code>IFormFile.OpenReadStream().ToArray()</code>.",
"Set <code>[RequestSizeLimit]</code> and <code>[RequestFormLimits]</code> at the action level, not globally, so only upload endpoints bear the larger limit."],
f'''
<h3>1. Accepting a file upload</h3>
{C(r"""
// Blog.Api/Controllers/UploadsController.cs
[ApiController]
[Route("api/[controller]")]
public class UploadsController(IFileStorage storage, ILogger<UploadsController> logger) : ControllerBase
{
    private static readonly string[] AllowedContentTypes =
        ["image/jpeg", "image/png", "image/webp"];

    private static readonly Dictionary<string, byte[]> MagicBytes = new()
    {
        ["image/jpeg"] = [0xFF, 0xD8, 0xFF],
        ["image/png"]  = [0x89, 0x50, 0x4E, 0x47],
        ["image/webp"] = [0x52, 0x49, 0x46, 0x46],   // "RIFF"
    };

    [HttpPost("cover")]
    [RequestSizeLimit(2 * 1024 * 1024)]                // 2 MB max
    [RequestFormLimits(MultipartBodyLengthLimit = 2 * 1024 * 1024)]
    public async Task<IActionResult> UploadCoverImage(
        IFormFile file,
        CancellationToken ct)
    {
        // 1. Content-type whitelist
        if (!AllowedContentTypes.Contains(file.ContentType))
            return BadRequest($"Only JPEG, PNG and WebP are allowed.");

        // 2. File size guard (belt + suspenders alongside the attribute)
        if (file.Length == 0 || file.Length > 2 * 1024 * 1024)
            return BadRequest("File must be 1 byte – 2 MB.");

        // 3. Magic-byte check
        if (!await HasValidMagicBytesAsync(file))
            return BadRequest("File content does not match its declared type.");

        // 4. Store with a safe, server-generated name
        string stored = await storage.SaveAsync(file, ct);

        logger.LogInformation("Cover image uploaded: {FileName} → {StoredPath}",
            file.FileName, stored);

        return Ok(new { url = $"/api/uploads/{stored}" });
    }

    private static async Task<bool> HasValidMagicBytesAsync(IFormFile file)
    {
        if (!MagicBytes.TryGetValue(file.ContentType, out byte[]? magic)) return false;

        byte[] header = new byte[magic.Length];
        await using var stream = file.OpenReadStream();
        int read = await stream.ReadAsync(header.AsMemory(0, magic.Length));
        return read == magic.Length && header.SequenceEqual(magic);
    }
}
""", "Blog.Api/Controllers/UploadsController.cs")}

<h3>2. IFileStorage abstraction and local implementation</h3>
{C(r"""
// Blog.Core/Interfaces/IFileStorage.cs
namespace Blog.Core.Interfaces;

public interface IFileStorage
{
    Task<string> SaveAsync(IFormFile file, CancellationToken ct);
    string GetPhysicalPath(string storedName);
    Task DeleteAsync(string storedName, CancellationToken ct);
}
""", "Blog.Core/Interfaces/IFileStorage.cs")}
{C(r"""
// Blog.Infrastructure/Storage/LocalFileStorage.cs
using Blog.Core.Interfaces;

namespace Blog.Infrastructure.Storage;

public sealed class LocalFileStorage : IFileStorage
{
    private readonly string _root;

    public LocalFileStorage(IConfiguration cfg)
    {
        // Stored outside wwwroot: "StoragePath": "/data/blog-uploads" in appsettings
        _root = cfg["StoragePath"] ?? Path.Combine(Directory.GetCurrentDirectory(), "uploads");
        Directory.CreateDirectory(_root);
    }

    public async Task<string> SaveAsync(IFormFile file, CancellationToken ct)
    {
        // Server-generated safe name; keep original extension only after re-checking content
        string ext = file.ContentType switch
        {
            "image/jpeg" => ".jpg",
            "image/png"  => ".png",
            "image/webp" => ".webp",
            _            => throw new InvalidOperationException("Unsupported type")
        };

        string stored = $"{Guid.NewGuid():N}{ext}";
        string full   = Path.Combine(_root, stored);

        await using var dest = new FileStream(full, FileMode.CreateNew, FileAccess.Write,
            FileShare.None, bufferSize: 81920, useAsync: true);
        await file.CopyToAsync(dest, ct);         // streaming: doesn't buffer in RAM

        return stored;
    }

    public string GetPhysicalPath(string storedName) =>
        Path.GetFullPath(Path.Combine(_root, storedName));  // GetFullPath prevents path traversal

    public async Task DeleteAsync(string storedName, CancellationToken ct)
    {
        string path = GetPhysicalPath(storedName);
        if (File.Exists(path))
            await Task.Run(() => File.Delete(path), ct);
    }
}
""", "Blog.Infrastructure/Storage/LocalFileStorage.cs")}

<h3>3. Downloading a file (range requests)</h3>
{C(r"""
// Blog.Api/Controllers/UploadsController.cs (download action)
[HttpGet("{storedName}")]
public IActionResult Download(string storedName)
{
    // Prevent path traversal: only allow simple file names
    if (storedName.Contains('/') || storedName.Contains('\\') || storedName.Contains(".."))
        return BadRequest("Invalid file name.");

    string path = _storage.GetPhysicalPath(storedName);
    if (!System.IO.File.Exists(path))
        return NotFound();

    // PhysicalFile automatically handles Range requests (resumable downloads)
    string contentType = Path.GetExtension(storedName).ToLowerInvariant() switch
    {
        ".jpg" or ".jpeg" => "image/jpeg",
        ".png"  => "image/png",
        ".webp" => "image/webp",
        _       => "application/octet-stream"
    };

    return PhysicalFile(path, contentType, enableRangeProcessing: true);
}
""")}
{tip("Set <code>enableRangeProcessing: true</code> in PhysicalFile so browsers and download managers can resume partial downloads with the HTTP Range header.")}

<h3>4. Size limit configuration in Kestrel</h3>
{C(r"""
// appsettings.json — Kestrel limits
{
  "Kestrel": {
    "Limits": {
      "MaxRequestBodySize": 2097152    // 2 MB global max (can be overridden per action)
    }
  }
}
""", lang="json")}
{warn("Path traversal attack: if you ever use user-supplied file names in Path.Combine, an attacker can supply '../../../etc/passwd'. Always use Path.GetFullPath and verify the result starts with the allowed root, or store only the GUID name and look up the real path in a database.")}
''',
["Storing uploaded files inside wwwroot — the web server serves them directly, bypassing your auth check.",
"Trusting IFormFile.ContentType — it's a client-supplied header; always verify magic bytes.",
"Using IFormFile.FileName in Path.Combine — allows path traversal attacks.",
"Buffering the whole file into a byte[] with ReadToEndAsync — exhausts memory on large uploads.",
"Forgetting [RequestSizeLimit] — the default 30 MB Kestrel limit may be too large."],
("40 min", [
    "Implement LocalFileStorage and wire it into the BlogApi. Upload a JPEG via curl and verify the file lands on disk with a GUID name.",
    "Modify the magic-byte check to also reject files whose first bytes claim to be an image but whose extension says .exe — confirm it returns 400.",
    "Add a GET download endpoint that serves the file with PhysicalFile. Use curl --range 0-99 to download only the first 100 bytes and confirm the response is 206 Partial Content."
]),
[("Why should uploaded files be stored outside wwwroot?","Files in wwwroot are served directly by the static-files middleware, bypassing controllers and authentication. A malicious .aspx or .php file (on IIS) could be executed. Store uploads outside wwwroot and serve them through a controller that checks permissions."),
("What are magic bytes?","Fixed byte sequences at the start of a file that identify its format. E.g. JPEG files start 0xFF 0xD8 0xFF. Verifying them prevents an attacker from renaming a script file as image.jpg and uploading it."),
("What HTTP status code is returned for a partial content download?","206 Partial Content, with Content-Range and ETag headers.")],
[("Basic","What is IFormFile?","An ASP.NET Core abstraction for a file part in a multipart/form-data HTTP request. It exposes the file name, content type, length and a stream to read its bytes."),
("Basic","Why not use the original file name when storing uploads?","Client-supplied names can contain path separators ('..', '/'), reserved characters, or executable extensions. Use a server-generated GUID as the stored name and keep the original in a database column for display only."),
("Basic","What does enableRangeProcessing in PhysicalFile do?","Causes ASP.NET Core to process the HTTP Range header, returning a 206 Partial Content response with only the requested byte range. This enables resumable and parallel downloads."),
("Intermediate","How do you prevent path traversal in a download endpoint?","1) Reject stored names that contain '/', '\\\\' or '..'. 2) Call Path.GetFullPath on the combined path. 3) Assert that the result starts with the allowed root directory. Only one of these checks alone is insufficient."),
("Intermediate","How do you stream a large file upload without buffering it in memory?","Use file.CopyToAsync(destination, ct) where destination is a FileStream opened with useAsync: true. This copies the multipart body stream directly to disk in fixed-size chunks, keeping memory usage flat regardless of file size."),
("Intermediate","What is the relationship between [RequestSizeLimit] and Kestrel's MaxRequestBodySize?","[RequestSizeLimit] overrides the Kestrel limit for a single action. It must be set at or below the Kestrel limit unless you also configure Kestrel's per-endpoint MaxRequestBodySize. Setting [RequestSizeLimit] alone does not raise the Kestrel ceiling.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project: BlogApi",
"Build a full Blog REST API applying every cross-cutting concern from this week: Post/Comment/Tag with EF Core, IExceptionHandler, Serilog, health checks, CORS, rate limiting, output cache, and file upload. Budget: about 4 hours.",
[("BlogApi","The week's micro-project: a production-ready ASP.NET Core 8 Blog API with cross-cutting concerns applied from the start."),
("Slug","A URL-safe string derived from the post title: 'Mastering LINQ in India' → 'mastering-linq-in-india'."),
("Publish workflow","Posts are created as Draft and explicitly published, changing their status and setting PublishedAt."),
("Nested comments","Comments have an optional ParentCommentId enabling threaded replies up to arbitrary depth."),
("Many-to-many tags","A Post can have many Tags and a Tag can belong to many Posts; EF Core maps this via a join table.")],
["Apply the DomainExceptionHandler and GlobalExceptionHandler from Day 1.",
"Wire in Serilog with two-stage bootstrap and UseSerilogRequestLogging from Day 2.",
"Map /health/live and /health/ready with database and memory checks from Day 3.",
"Set up a CORS policy for http://localhost:3000 from Day 3.",
"Apply a token-bucket rate limiter on comment creation from Day 4.",
"Apply OutputCache with tag eviction on the post list and single-post endpoints from Day 4."],
f'''
<h3>Scaffold</h3>
{C(r"""
mkdir BlogApi && cd BlogApi
dotnet new sln
dotnet new classlib -n Blog.Core            && dotnet sln add Blog.Core
dotnet new classlib -n Blog.Infrastructure  && dotnet sln add Blog.Infrastructure
dotnet new webapi   -n Blog.Api             && dotnet sln add Blog.Api

cd Blog.Core && dotnet add package Microsoft.Extensions.DependencyInjection.Abstractions
cd ../Blog.Infrastructure
dotnet add package Microsoft.EntityFrameworkCore.SqlServer
dotnet add package Microsoft.EntityFrameworkCore.Design
cd ../Blog.Api
dotnet add reference ../Blog.Core
dotnet add reference ../Blog.Infrastructure
dotnet add package Serilog.AspNetCore
dotnet add package Serilog.Sinks.File
dotnet add package Serilog.Sinks.Seq
dotnet add package Serilog.Enrichers.Environment
dotnet add package Serilog.Enrichers.Thread
dotnet add package Microsoft.AspNetCore.Diagnostics.HealthChecks
""", lang="bash")}

<h3>Folder structure</h3>
{C(r"""
BlogApi/
├── Blog.Core/
│   ├── Exceptions/     (DomainException, NotFoundException, ConflictException, UnprocessableException)
│   ├── Interfaces/     (IPostService, ICommentService, IFileStorage)
│   └── Models/         (Post, Comment, Tag, PostStatus)
├── Blog.Infrastructure/
│   ├── Data/           (BlogDbContext)
│   ├── Repositories/   (PostRepository, CommentRepository)
│   └── Storage/        (LocalFileStorage)
└── Blog.Api/
    ├── Controllers/    (PostsController, CommentsController, UploadsController)
    ├── Exceptions/     (DomainExceptionHandler, GlobalExceptionHandler)
    ├── HealthChecks/   (DatabaseHealthCheck)
    └── Program.cs
""", lang="text")}

<h3>Core models</h3>
{C(r"""
// Blog.Core/Models/Post.cs
namespace Blog.Core.Models;

public enum PostStatus { Draft, Published }

public class Post
{
    public int    Id          { get; set; }
    public string Title       { get; set; } = "";
    public string Slug        { get; set; } = "";
    public string Content     { get; set; } = "";
    public string AuthorName  { get; set; } = "";   // e.g. "Priya Sharma"
    public string? CoverImage { get; set; }
    public PostStatus Status  { get; set; } = PostStatus.Draft;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? PublishedAt { get; set; }

    public ICollection<Comment> Comments { get; set; } = [];
    public ICollection<Tag>     Tags     { get; set; } = [];
}

public class Comment
{
    public int    Id              { get; set; }
    public string Body            { get; set; } = "";
    public string AuthorName      { get; set; } = "";
    public DateTime CreatedAt     { get; set; } = DateTime.UtcNow;
    public int    PostId          { get; set; }
    public Post   Post            { get; set; } = null!;
    public int?   ParentCommentId { get; set; }
    public Comment? Parent        { get; set; }
    public ICollection<Comment> Replies { get; set; } = [];
}

public class Tag
{
    public int    Id    { get; set; }
    public string Name  { get; set; } = "";
    public string Slug  { get; set; } = "";
    public ICollection<Post> Posts { get; set; } = [];
}
""", "Blog.Core/Models/Post.cs")}

<h3>EF Core DbContext</h3>
{C(r"""
// Blog.Infrastructure/Data/BlogDbContext.cs
using Blog.Core.Models;
using Microsoft.EntityFrameworkCore;

namespace Blog.Infrastructure.Data;

public class BlogDbContext(DbContextOptions<BlogDbContext> opts) : DbContext(opts)
{
    public DbSet<Post>    Posts    => Set<Post>();
    public DbSet<Comment> Comments => Set<Comment>();
    public DbSet<Tag>     Tags     => Set<Tag>();

    protected override void OnModelCreating(ModelBuilder mb)
    {
        mb.Entity<Post>(b =>
        {
            b.HasIndex(p => p.Slug).IsUnique();
            b.Property(p => p.Title).HasMaxLength(300);
            b.Property(p => p.Slug).HasMaxLength(300);
            b.HasMany(p => p.Comments).WithOne(c => c.Post)
             .HasForeignKey(c => c.PostId).OnDelete(DeleteBehavior.Cascade);
            b.HasMany(p => p.Tags).WithMany(t => t.Posts)
             .UsingEntity("PostTag");
        });

        mb.Entity<Comment>(b =>
        {
            b.HasOne(c => c.Parent).WithMany(c => c.Replies)
             .HasForeignKey(c => c.ParentCommentId).OnDelete(DeleteBehavior.Restrict);
        });

        mb.Entity<Tag>(b =>
        {
            b.HasIndex(t => t.Slug).IsUnique();
            b.Property(t => t.Name).HasMaxLength(80);
        });
    }
}
""", "Blog.Infrastructure/Data/BlogDbContext.cs")}

<h3>PostsController — full implementation</h3>
{C(r"""
// Blog.Api/Controllers/PostsController.cs
using Blog.Core.Exceptions;
using Blog.Core.Models;
using Blog.Infrastructure.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.OutputCaching;
using Microsoft.EntityFrameworkCore;

namespace Blog.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class PostsController(BlogDbContext db, IOutputCacheStore cacheStore, ILogger<PostsController> logger)
    : ControllerBase
{
    [HttpGet]
    [OutputCache(PolicyName = "postList")]
    public async Task<IActionResult> List(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 10,
        [FromQuery] string? tag = null,
        CancellationToken ct = default)
    {
        var query = db.Posts
            .Include(p => p.Tags)
            .Where(p => p.Status == PostStatus.Published);

        if (!string.IsNullOrWhiteSpace(tag))
            query = query.Where(p => p.Tags.Any(t => t.Slug == tag));

        int total = await query.CountAsync(ct);
        var items = await query
            .OrderByDescending(p => p.PublishedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Select(p => new { p.Id, p.Title, p.Slug, p.AuthorName, p.PublishedAt,
                               Tags = p.Tags.Select(t => t.Name) })
            .ToListAsync(ct);

        return Ok(new { page, pageSize, total, items });
    }

    [HttpGet("{slug}")]
    [OutputCache(PolicyName = "singlePost")]
    public async Task<IActionResult> Get(string slug, CancellationToken ct)
    {
        var post = await db.Posts
            .Include(p => p.Tags)
            .Include(p => p.Comments.Where(c => c.ParentCommentId == null))
                .ThenInclude(c => c.Replies)
            .FirstOrDefaultAsync(p => p.Slug == slug && p.Status == PostStatus.Published, ct);

        if (post is null) throw new NotFoundException("Post", slug);

        return Ok(post);
    }

    [HttpPost]
    public async Task<IActionResult> Create(CreatePostRequest req, CancellationToken ct)
    {
        string slug = Slugify(req.Title);

        if (await db.Posts.AnyAsync(p => p.Slug == slug, ct))
            throw new ConflictException($"A post with slug '{slug}' already exists.");

        var post = new Post
        {
            Title      = req.Title,
            Slug       = slug,
            Content    = req.Content,
            AuthorName = req.AuthorName,
            Status     = PostStatus.Draft
        };
        db.Posts.Add(post);
        await db.SaveChangesAsync(ct);
        await cacheStore.EvictByTagAsync("posts", ct);
        logger.LogInformation("Post {Slug} created by {Author}", slug, req.AuthorName);
        return CreatedAtAction(nameof(Get), new { slug = post.Slug }, new { post.Id, post.Slug });
    }

    [HttpPost("{id:int}/publish")]
    public async Task<IActionResult> Publish(int id, CancellationToken ct)
    {
        var post = await db.Posts.FindAsync([id], ct)
            ?? throw new NotFoundException("Post", id);

        if (post.Status == PostStatus.Published)
            throw new ConflictException($"Post '{post.Slug}' is already published.");

        post.Status      = PostStatus.Published;
        post.PublishedAt = DateTime.UtcNow;
        await db.SaveChangesAsync(ct);
        await cacheStore.EvictByTagAsync("posts", ct);
        return NoContent();
    }

    private static string Slugify(string title) =>
        System.Text.RegularExpressions.Regex.Replace(
            title.Trim().ToLowerInvariant(), @"[^a-z0-9]+", "-")
        .Trim('-');

    public record CreatePostRequest(string Title, string Content, string AuthorName);
}
""", "Blog.Api/Controllers/PostsController.cs")}

<h3>CommentsController with rate limiting</h3>
{C(r"""
// Blog.Api/Controllers/CommentsController.cs
using Blog.Core.Exceptions;
using Blog.Core.Models;
using Blog.Infrastructure.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;

namespace Blog.Api.Controllers;

[ApiController]
[Route("api/posts/{{postId}}/comments")]
public class CommentsController(BlogDbContext db) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> List(int postId, CancellationToken ct)
    {
        bool exists = await db.Posts.AnyAsync(p => p.Id == postId, ct);
        if (!exists) throw new NotFoundException("Post", postId);

        var comments = await db.Comments
            .Where(c => c.PostId == postId && c.ParentCommentId == null)
            .Include(c => c.Replies)
            .OrderByDescending(c => c.CreatedAt)
            .ToListAsync(ct);

        return Ok(comments);
    }

    [HttpPost]
    [EnableRateLimiting("commentCreate")]   // token-bucket from Program.cs
    public async Task<IActionResult> Create(int postId, CreateCommentRequest req, CancellationToken ct)
    {
        var post = await db.Posts.FindAsync([postId], ct)
            ?? throw new NotFoundException("Post", postId);

        if (post.Status != PostStatus.Published)
            throw new UnprocessableException("Cannot comment on a draft post.");

        if (req.ParentCommentId.HasValue)
        {
            bool parentExists = await db.Comments
                .AnyAsync(c => c.Id == req.ParentCommentId && c.PostId == postId, ct);
            if (!parentExists)
                throw new NotFoundException("Comment", req.ParentCommentId);
        }

        var comment = new Comment
        {
            PostId          = postId,
            Body            = req.Body,
            AuthorName      = req.AuthorName,
            ParentCommentId = req.ParentCommentId
        };
        db.Comments.Add(comment);
        await db.SaveChangesAsync(ct);
        return CreatedAtAction(nameof(List), new { postId }, new { comment.Id });
    }

    public record CreateCommentRequest(string Body, string AuthorName, int? ParentCommentId);
}
""", "Blog.Api/Controllers/CommentsController.cs")}

<h3>Program.cs — full wiring</h3>
{C(r"""
// Blog.Api/Program.cs
using System.Threading.RateLimiting;
using Blog.Api.Exceptions;
using Blog.Api.HealthChecks;
using Blog.Core.Interfaces;
using Blog.Infrastructure.Data;
using Blog.Infrastructure.Storage;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using Serilog;

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Warning()
    .WriteTo.Console()
    .CreateBootstrapLogger();

try
{
    var builder = WebApplication.CreateBuilder(args);

    builder.Host.UseSerilog((ctx, _, cfg) =>
        cfg.ReadFrom.Configuration(ctx.Configuration)
           .Enrich.FromLogContext()
           .Enrich.WithMachineName()
           .Enrich.WithEnvironmentName());

    builder.Services.AddDbContext<BlogDbContext>(opts =>
        opts.UseSqlServer(builder.Configuration.GetConnectionString("Blog")));

    builder.Services.AddSingleton<IFileStorage, LocalFileStorage>();

    builder.Services.AddProblemDetails();
    builder.Services.AddExceptionHandler<DomainExceptionHandler>();
    builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

    builder.Services.AddHealthChecks()
        .AddCheck<DatabaseHealthCheck>("database", tags: ["ready"])
        .AddCheck<MemoryHealthCheck>("memory",    tags: ["live", "ready"]);

    builder.Services.AddCors(opts =>
        opts.AddPolicy("Frontend", p =>
            p.WithOrigins("http://localhost:3000", "https://blog.example.in")
             .AllowAnyHeader()
             .AllowAnyMethod()
             .AllowCredentials()));

    builder.Services.AddRateLimiter(opts =>
    {
        opts.AddTokenBucketLimiter("commentCreate", o =>
        {
            o.TokenLimit          = 5;
            o.ReplenishmentPeriod = TimeSpan.FromMinutes(1);
            o.TokensPerPeriod     = 2;
            o.AutoReplenishment   = true;
        });
        opts.OnRejected = async (ctx, ct) =>
        {
            ctx.HttpContext.Response.StatusCode = 429;
            if (ctx.Lease.TryGetMetadata(MetadataName.RetryAfter, out var wait))
                ctx.HttpContext.Response.Headers.RetryAfter = ((int)wait.TotalSeconds).ToString();
            await ctx.HttpContext.Response.WriteAsync("Too many requests.", ct);
        };
    });

    builder.Services.AddOutputCache(opts =>
    {
        opts.AddPolicy("postList",   b => b.Expire(TimeSpan.FromMinutes(2))
                                           .SetVaryByQuery("page", "pageSize", "tag")
                                           .Tag("posts"));
        opts.AddPolicy("singlePost", b => b.Expire(TimeSpan.FromMinutes(5))
                                           .SetVaryByRouteValue("slug")
                                           .Tag("posts"));
        opts.AddPolicy("noCache",    b => b.NoStore());
    });

    builder.Services.AddControllers();

    var app = builder.Build();

    app.UseExceptionHandler();
    app.UseSerilogRequestLogging();
    app.UseCors("Frontend");
    app.UseRateLimiter();
    app.UseOutputCache();
    app.MapControllers();
    app.MapHealthChecks("/health/live",  new() { Predicate = c => c.Tags.Contains("live")  });
    app.MapHealthChecks("/health/ready", new() { Predicate = c => c.Tags.Contains("ready") });

    app.Run();
}
catch (Exception ex) when (ex is not HostAbortedException)
{
    Log.Fatal(ex, "BlogApi startup failed");
}
finally
{
    Log.CloseAndFlush();
}
""", "Blog.Api/Program.cs")}

<h3>Migration and run commands</h3>
{C(r"""
# Start SQL Server in Docker
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=Blog@12345" \
  -p 1433:1433 --name blog-sql \
  mcr.microsoft.com/mssql/server:2022-latest

# In Blog.Infrastructure:
dotnet ef migrations add InitialCreate --startup-project ../Blog.Api
dotnet ef database update  --startup-project ../Blog.Api

# Run the API
cd Blog.Api && dotnet run
""", lang="bash")}

<h3>curl smoke tests</h3>
{C(r"""
# Create a post
curl -s -X POST http://localhost:5000/api/posts \
  -H "Content-Type: application/json" \
  -d '{"title":"Mastering LINQ in India","content":"LINQ makes data access elegant...","authorName":"Priya Sharma"}'
# → {"id":1,"slug":"mastering-linq-in-india"}

# Publish it
curl -s -X POST http://localhost:5000/api/posts/1/publish

# List posts (cached after first hit)
curl -s http://localhost:5000/api/posts
curl -v http://localhost:5000/api/posts   # second hit shows Age header

# Add a comment (rate-limited)
curl -s -X POST http://localhost:5000/api/posts/1/comments \
  -H "Content-Type: application/json" \
  -d '{"body":"Great article!","authorName":"Ravi Kumar","parentCommentId":null}'

# Trigger 429 by running the comment POST 6+ times in quick succession
for i in {1..7}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:5000/api/posts/1/comments \
    -H "Content-Type: application/json" \
    -d '{"body":"Spam","authorName":"Bot","parentCommentId":null}'
done
# Expected: 201 201 201 201 201 429 429

# Health checks
curl http://localhost:5000/health/live
curl http://localhost:5000/health/ready

# 404 via IExceptionHandler
curl -s http://localhost:5000/api/posts/nonexistent-slug
# → {"title":"NotFound","status":404,"detail":"Post 'nonexistent-slug' was not found.","traceId":"..."}
""", lang="bash")}

<h3>Stretch goals</h3>
{C(r"""
// 1. Add PUT /api/posts/{id} that updates title + content and evicts cache
// 2. Add DELETE /api/posts/{id} (soft-delete: set Status = Archived)
// 3. Add tag management: POST /api/tags, GET /api/posts?tag=linq
// 4. Rate-limit the GET /api/posts list to 60 req/min globally using FixedWindow
// 5. Add ApproximateCount to MemoryHealthCheck using GC.GetTotalMemory(false)
""", lang="csharp")}
''',
iqs=[("Basic","Why is the two-stage Serilog bootstrap necessary?","Without it, exceptions during host.Build() (e.g. a misconfigured connection string) would swallow silently. The bootstrap logger writes to Console before the host is ready, so startup failures are always visible."),
("Basic","Why is UseExceptionHandler() placed first in the pipeline?","Middleware runs in registration order. Placing UseExceptionHandler first ensures it wraps all subsequent middleware, catching exceptions from routing, authentication, controllers and output caching."),
("Intermediate","How do you prevent OutputCache from serving stale post data after a write?","Assign a tag to all post-list and single-post policies (e.g. 'posts'). After any create/update/delete call cacheStore.EvictByTagAsync('posts', ct). This removes all entries with that tag from the in-process store atomically."),
("Intermediate","How does the token-bucket rate limiter differ from a fixed-window limiter for comment spam prevention?","Token bucket replenishes at a smooth rate and allows short bursts up to the bucket size; a fixed window resets entirely and can be gamed by sending all requests at the boundary. For comment creation, token bucket distributes limits more fairly over time and is harder to abuse.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Finish BlogApi, Try-to-Break, README and Revision",
"Complete the cover-image upload feature, run a systematic try-to-break table, write the project README, commit, and revise the week's cross-cutting concepts.",
[("Cross-cutting concern","A behaviour that spans all layers and features — logging, error handling, security, caching, rate limiting — applied once, consistently, without polluting business logic."),
("Middleware pipeline order","The sequence in which ASP.NET Core middleware executes; order matters because each middleware wraps the next."),
("Defense in depth","Applying multiple independent checks (content-type + file size + magic bytes) so breaking one check alone is not sufficient."),
("Idempotent caching","Only caching GET/HEAD endpoints; write operations (POST/PUT/DELETE) must be NoStore so they never serve stale mutating responses."),
("Graceful degradation","Using HealthStatus.Degraded for non-critical checks so the pod isn't restarted for minor issues.")],
["Health checks, CORS, rate limiting and output cache are configured in services, applied in middleware, and used in endpoints — always check all three layers.",
"Serilog's two-stage bootstrap + Log.CloseAndFlush() protects both startup and shutdown.",
"Magic-byte validation must rewind the stream to position 0 after reading — or use the approach of opening a fresh stream for validation.",
"Tag eviction from OutputCache is synchronous within the request; don't fire it in a background thread without a CancellationToken safety net.",
"The correct middleware order: ExceptionHandler → Serilog → CORS → RateLimit → OutputCache → Routing → Auth → Controllers."],
f'''
<h3>1. Cover-image upload — complete feature</h3>
{C(r"""
// Blog.Api/Controllers/PostsController.cs — add upload action
[HttpPost("{id:int}/cover")]
[RequestSizeLimit(2 * 1024 * 1024)]
[RequestFormLimits(MultipartBodyLengthLimit = 2 * 1024 * 1024)]
public async Task<IActionResult> UploadCover(
    int id,
    IFormFile file,
    [FromServices] IFileStorage storage,
    CancellationToken ct)
{
    var post = await db.Posts.FindAsync([id], ct)
        ?? throw new NotFoundException("Post", id);

    // Validate content type
    string[] allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.Contains(file.ContentType))
        throw new UnprocessableException("Only JPEG, PNG and WebP images are accepted.");

    if (file.Length > 2 * 1024 * 1024)
        throw new UnprocessableException("Cover image must be 2 MB or smaller.");

    // Magic-byte check
    byte[] buf = new byte[8];
    await using (var s = file.OpenReadStream()) await s.ReadAsync(buf.AsMemory(0, 8), ct);

    bool valid = file.ContentType switch
    {
        "image/jpeg" => buf[0] == 0xFF && buf[1] == 0xD8 && buf[2] == 0xFF,
        "image/png"  => buf[0] == 0x89 && buf[1] == 0x50 && buf[2] == 0x4E && buf[3] == 0x47,
        "image/webp" => buf[0] == 0x52 && buf[1] == 0x49 && buf[2] == 0x46 && buf[3] == 0x46,
        _            => false
    };
    if (!valid) throw new UnprocessableException("File content does not match declared type.");

    // Delete old cover if present
    if (post.CoverImage is not null)
        await storage.DeleteAsync(post.CoverImage, ct);

    string stored = await storage.SaveAsync(file, ct);
    post.CoverImage = stored;
    await db.SaveChangesAsync(ct);
    await cacheStore.EvictByTagAsync("posts", ct);

    return Ok(new { url = $"/api/uploads/{stored}" });
}
""", "Blog.Api/Controllers/PostsController.cs (cover)")}

<h3>2. MemoryHealthCheck</h3>
{C(r"""
// Blog.Api/HealthChecks/MemoryHealthCheck.cs
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace Blog.Api.HealthChecks;

public sealed class MemoryHealthCheck : IHealthCheck
{
    private const long DegradedThreshold = 200 * 1024 * 1024;  // 200 MB

    public Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken ct = default)
    {
        long usedBytes = GC.GetTotalMemory(forceFullCollection: false);

        return Task.FromResult(usedBytes < DegradedThreshold
            ? HealthCheckResult.Healthy($"Memory: {usedBytes / 1024 / 1024} MB")
            : HealthCheckResult.Degraded($"Memory high: {usedBytes / 1024 / 1024} MB (> 200 MB)"));
    }
}
""", "Blog.Api/HealthChecks/MemoryHealthCheck.cs")}

<h3>3. Try-to-break table</h3>
{table(["Scenario","Expected behaviour"],[
["POST /api/posts with duplicate slug","409 Conflict with ProblemDetails"],
["GET /api/posts/nonexistent-slug","404 Not Found with ProblemDetails + traceId"],
["POST /api/posts/1/comments 7 times in 60 s","First 5 succeed (201), next 2 return 429 + Retry-After"],
["GET /api/posts (cached), then POST new post, then GET again","First GET cached; after POST cache evicted; second GET is a fresh DB query"],
["POST /api/posts/1/cover with a text/plain file","400 or 422 with 'Only JPEG/PNG/WebP' message"],
["POST /api/posts/1/cover with a JPEG renamed to .exe but correct magic bytes","422 from content-type whitelist check (ContentType will be application/octet-stream)"],
["POST /api/posts/1/cover with a file renamed image.jpg but containing a PHP script (wrong magic bytes)","422 Unprocessable: magic-byte check fails"],
["Shut down SQL Server; GET /health/ready","503 Service Unavailable, entries show database: Unhealthy"],
["Shut down SQL Server; GET /health/live","200 Healthy (liveness only checks memory)"],
["OPTIONS /api/posts from http://evil.example.com","No Access-Control-Allow-Origin header in response (origin not in policy)"],
["Throw new Exception(\"unexpected\") in a service","500 with generic message in production; stack trace only in Development"],
["POST /api/posts/1/comments on a draft post","422 Unprocessable via UnprocessableException → DomainExceptionHandler"]])}

<h3>4. Week-19 checklist</h3>
{C(r"""
[ ] IExceptionHandler — domain hierarchy, chained handlers, ProblemDetails + traceId
[ ] Serilog — two-stage bootstrap, appsettings sinks, UseSerilogRequestLogging, Log.CloseAndFlush
[ ] Health checks — IHealthCheck, liveness vs readiness, DbContext check, /health/live + /health/ready
[ ] CORS — named policy, AllowAnyOrigin pitfall, preflight (OPTIONS)
[ ] Rate limiting — FixedWindow / SlidingWindow / TokenBucket, partitioned, 429 + Retry-After
[ ] OutputCache — policies, vary-by, tag eviction, noCache on writes
[ ] File upload — IFormFile, content-type whitelist, magic bytes, safe names, streaming, range download
[ ] BlogApi built — Post/Comment/Tag, draft/publish, nested comments, all concerns applied
[ ] curl smoke tests pass for posts, comments, health, 429, ProblemDetails
""", lang="text")}

<h3>5. README template</h3>
{C(r"""
# BlogApi

A production-ready ASP.NET Core 8 Blog REST API demonstrating cross-cutting concerns.

## Features
- Post CRUD with draft/publish workflow and URL slugs
- Nested comments (threaded replies) with token-bucket rate limiting
- Many-to-many Tags
- Cover-image upload with magic-byte validation (JPEG/PNG/WebP, max 2 MB)
- Global exception handling (IExceptionHandler, ProblemDetails, traceId)
- Structured logging (Serilog → Console + File + Seq)
- Health checks: /health/live (memory) and /health/ready (db + memory)
- CORS for http://localhost:3000 and https://blog.example.in
- Output cache on post list and single post, tag eviction on write

## Prerequisites
- .NET 8 SDK
- Docker (SQL Server 2022, Seq)

## Quickstart
```bash
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=Blog@12345" -p 1433:1433 \\
  mcr.microsoft.com/mssql/server:2022-latest

docker run --rm -p 5341:5341 -p 5342:80 datalust/seq:latest

cd Blog.Infrastructure
dotnet ef database update --startup-project ../Blog.Api

cd ../Blog.Api
dotnet run
```

## Cross-cutting middleware order
ExceptionHandler → Serilog → CORS → RateLimiter → OutputCache → Routing → Controllers
""", lang="text")}

<h3>6. Git</h3>
{C(r"""
cd BlogApi
git init && git add .
git commit -m "Week 19: BlogApi with cross-cutting concerns"
git remote add origin https://github.com/YOUR_HANDLE/dotnet-roadmap.git
git push -u origin main
""", lang="bash")}

<h3>7. Week-19 quiz — predict the output or does it compile?</h3>

<details><summary>Q1. How many IExceptionHandler implementations are invoked for a NotFoundException?</summary>
{C(r"""
// DomainExceptionHandler is registered first; NotFoundException IS a DomainException.
// DomainExceptionHandler.TryHandleAsync returns true.
// GlobalExceptionHandler is never called.
""", lang="text")}
<b>One — only DomainExceptionHandler.</b> It matches the exception type and returns true, short-circuiting the chain.</details>

<details><summary>Q2. What does this Serilog call log?</summary>
{C(r"""
string slug = "mastering-linq-in-india";
int views = 1420;
logger.LogInformation($"Post {slug} has {views} views");
""")}<b>A plain string: "Post mastering-linq-in-india has 1420 views".</b> The $ makes this string interpolation; Serilog receives a pre-built string with no structured properties. Drop the $ to capture Slug and Views as filterable fields.</details>

<details><summary>Q3. Does this compile and what does it do at startup?</summary>
{C(r"""
builder.Services.AddCors(opts =>
    opts.AddPolicy("Open", p =>
        p.AllowAnyOrigin().AllowCredentials()));
""")}<b>It compiles but throws InvalidOperationException at app.Build().</b> AllowAnyOrigin combined with AllowCredentials violates the CORS spec; ASP.NET Core 5+ rejects this combination at startup.</details>

<details><summary>Q4. A GET /api/posts request comes in. What determines whether OutputCache serves a cached response or hits the DB?</summary>
{C(r"""
// The policy is: Expire(2 min), SetVaryByQuery("page","pageSize","tag"), Tag("posts")
// Request 1: GET /api/posts?page=1&pageSize=10 → DB hit, response cached under key (page=1,pageSize=10)
// Request 2: GET /api/posts?page=1&pageSize=10 within 2 min → cache hit
// Request 3: GET /api/posts?page=2&pageSize=10 → different vary-by key → DB hit
// After POST /api/posts and EvictByTagAsync("posts") → all entries removed → next request is DB hit
""", lang="text")}
<b>The vary-by query parameters and the tag eviction state.</b> Each combination of page/pageSize/tag is a separate cache entry; eviction by tag removes them all.</details>

<details><summary>Q5. A user sends 6 comment POST requests in 10 seconds. The token-bucket policy is: TokenLimit=5, ReplenishmentPeriod=1 min, TokensPerPeriod=2. What happens?</summary>
{C(r"""
// Bucket starts at 5. Each request costs 1 token.
// Requests 1–5: tokens 5→4→3→2→1→0, all succeed (HTTP 201)
// Request 6:    bucket is at 0, no token available → HTTP 429
// After 30 s:   1 token replenished (2 per 60 s = 1 per 30 s) → next request succeeds
""", lang="text")}
<b>Requests 1–5 get 201; request 6 gets 429 Too Many Requests with Retry-After ~30 s.</b></details>

<div class="note tip"><b>Next week:</b> Week 20 — Authentication and Authorization: JWT bearer tokens, ASP.NET Core Identity, role-based and policy-based authorization, refresh tokens, and securing the BlogApi with user accounts and author-only endpoints.</div>
''',
iqs=[("Basic","What is the correct middleware order for a production ASP.NET Core 8 API?","UseExceptionHandler → UseSerilogRequestLogging → UseCors → UseRateLimiter → UseOutputCache → UseRouting → UseAuthentication → UseAuthorization → MapControllers. ExceptionHandler must be first so it catches all subsequent errors; CORS must precede auth so OPTIONS preflights aren't rejected."),
("Basic","What are magic bytes and why are they checked in addition to ContentType?","Magic bytes are file-format signatures at the start of a file, independent of its declared MIME type. An attacker can upload a PHP script as image.jpg with ContentType: image/jpeg; magic-byte verification catches this by reading the actual file header."),
("Intermediate","How does IExceptionHandler compose with the existing UseExceptionHandler middleware?","UseExceptionHandler() (no path) in .NET 8 wraps the pipeline and, on an unhandled exception, iterates the registered IExceptionHandler implementations in DI order, calling TryHandleAsync on each until one returns true. If none handles it, a default 500 response is generated."),
("Intermediate","Why should OutputCache policies on write endpoints use NoStore?","An endpoint that modifies data must never serve a cached response — it would return stale data to the client and might skip executing the mutation. NoStore tells the middleware to bypass the cache entirely for that endpoint, both for reading and writing.")])

# ===================== ASSEMBLE =====================
days = "\n".join([d1, d2, d3, d4, d5, d6, d7])

cards = [
    (1, "MON", "Global Exception Handling",        "IExceptionHandler",   "IExceptionHandler chain, ProblemDetails, domain→HTTP mapping, traceId.",    "2 hrs"),
    (2, "TUE", "Structured Logging with Serilog",  "Serilog",             "Two-stage bootstrap, sinks, enrichers, request logging, level overrides.",  "2 hrs"),
    (3, "WED", "Health Checks and CORS",           "Health · CORS",        "Liveness vs readiness, custom IHealthCheck, named CORS policies, preflight.","2 hrs"),
    (4, "THU", "Rate Limiting and Output Caching", "RateLimit · Cache",    "Fixed/sliding/token-bucket, partitioned, 429, OutputCache tag eviction.",   "2 hrs"),
    (5, "FRI", "File Upload and Download",         "File Upload",          "IFormFile, magic bytes, safe names, streaming, PhysicalFile, range.",        "2 hrs"),
    (6, "SAT", "Micro-project: BlogApi",           "Project: BlogApi",     "Post/Comment/Tag, draft/publish, all cross-cutting concerns applied.",       "4 hrs"),
    (7, "SUN", "Finish, Try-to-Break and Revision","Finish &amp; Revise",  "Cover upload, try-to-break table, checklist, quiz, README, git.",            "4 hrs"),
]

build(
    "/home/claude/build/week04.html",
    "/home/claude/build/week19.html",
    19,
    "Week 19 — Cross-cutting Concerns",
    "Phase 2",
    "~18 hrs",
    ["Phase 2 · Week 19 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "Blog API"],
    "Real APIs don't just handle happy paths. This week you'll add the production scaffolding every ASP.NET Core API needs: centralised exception handling with RFC 7807 ProblemDetails, structured Serilog logging with Seq, health-check endpoints for Kubernetes, CORS policies for your front end, rate limiting to stop comment spam, server-side output caching with tag eviction, and safe file upload with magic-byte validation — all applied to the BlogApi micro-project.",
    cards,
    days
)
print("built week19")
