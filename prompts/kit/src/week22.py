import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1  MON =================
d1 = day(1, "MON", "Production-readiness checklist for ASP.NET Core APIs",
"Audit every API project from Weeks 17–21 against a production checklist and apply at least six concrete before/after fixes.",
[("ProblemDetails","RFC 7807 JSON error envelope: type, title, status, detail, instance; returned by <code>AddProblemDetails()</code>."),
("Health check","An endpoint (<code>/healthz</code>) that probes liveness/readiness so load balancers and k8s know if the pod is healthy."),
("Rate limiting","Middleware that throttles callers (fixed window, sliding window, token bucket, concurrency) so one client can't starve others."),
("Paging cap","A server-side maximum on <code>pageSize</code> (e.g. 100) that prevents a single request fetching millions of rows."),
("CancellationToken","Propagated from the HTTP context; pass it into every <code>await</code> so a disconnected client frees the database connection."),
("Connection-string hygiene","Storing connection strings in <code>appsettings.Development.json</code> (git-ignored), user-secrets, or environment variables — never in source control."),
("PII in logs","Logging emails, passwords, card numbers, Aadhaar IDs etc. Breaking regulation (DPDP Act in India) and leaking to log aggregators."),
("Auth on mutations","Requiring <code>[Authorize]</code> (or policy) on every POST/PUT/PATCH/DELETE endpoint. Anonymous writes are a critical vulnerability."),
("Migration committed","Every <code>dotnet ef migrations add &lt;Name&gt;</code> output committed to source control so another developer (or CI) gets the same schema."),
("Async all the way","Every I/O call uses <code>await</code> + an <code>Async</code> method (no <code>.Result</code> or <code>.Wait()</code>) to avoid thread-pool starvation."),
("Status-code contract","200 OK, 201 Created with Location header, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict."),
("Idempotency","GET/PUT/DELETE are safe to retry. POST is not (unless given an idempotency key).")],
["Run the checklist top-to-bottom for each project before you call it production-ready.",
"<code>AddProblemDetails()</code> + <code>UseExceptionHandler</code> together convert unhandled exceptions to ProblemDetails automatically.",
"Use <code>builder.Services.AddHealthChecks().AddSqlServer(connStr)</code> (requires the <code>AspNetCore.HealthChecks.SqlServer</code> NuGet package) in production.",
"<code>RateLimiterOptions</code> lives in the built-in <code>Microsoft.AspNetCore.RateLimiting</code> namespace (.NET 7+); no extra NuGet needed.",
"User-secrets (<code>dotnet user-secrets init</code>) store dev secrets outside the project folder, never in git.",
"Always log <em>that</em> an action happened, never <em>what</em> the sensitive value was."],
f'''
<h3>1. Status-code contract</h3>
<p>Every endpoint must return the right status code, not <code>200 OK</code> for everything.</p>
{table(["Scenario","Correct status","Minimal code"],[
["Item created","201 + Location header","<code>Results.CreatedAtRoute(...)</code>"],
["Found and returned","200","<code>Results.Ok(dto)</code>"],
["No content (delete)","204","<code>Results.NoContent()</code>"],
["Validation failure","400 + ProblemDetails","<code>Results.ValidationProblem(errors)</code>"],
["Not authenticated","401","Automatic when <code>[Authorize]</code> is on"],
["Authenticated but no access","403","<code>Results.Forbid()</code>"],
["Entity not found","404","<code>Results.NotFound()</code> or <code>Results.Problem(404)</code>"],
["Duplicate / conflict","409","<code>Results.Conflict()</code>"]])}
{C(r"""
// BEFORE: everything returns 200
app.MapPost("/api/products", (ProductDto dto, AppDb db) =>
{
    var product = new Product { Name = dto.Name, Price = dto.Price };
    db.Products.Add(product);
    db.SaveChanges();
    return Results.Ok(product);    // ❌ should be 201 with a location
});

// AFTER: 201 + Location
app.MapPost("/api/products", async (ProductDto dto, AppDb db, CancellationToken ct) =>
{
    var product = new Product { Name = dto.Name, Price = dto.Price };
    db.Products.Add(product);
    await db.SaveChangesAsync(ct); // ✓ async + CancellationToken
    return Results.CreatedAtRoute("GetProduct", new {{ id = product.Id }}, product);
}).RequireAuthorization();         // ✓ auth on mutation
""", "Fix1_StatusCodes.cs")}

<h3>2. ProblemDetails — consistent error shape</h3>
{C(r"""
// Program.cs
builder.Services.AddProblemDetails();          // sets up the RFC 7807 factory
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

app.UseExceptionHandler();                     // catches unhandled exceptions → ProblemDetails 500
app.UseStatusCodePages();                      // 404 on a missing route → ProblemDetails 404
""", "ProblemDetails_Setup.cs")}
{C(r"""
// GlobalExceptionHandler.cs
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

public sealed class GlobalExceptionHandler(IProblemDetailsService problemDetails)
    : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, Exception exception, CancellationToken ct)
    {
        // Log the exception here (without PII!)
        httpContext.Response.StatusCode = exception is NotFoundException ? 404 : 500;
        return await problemDetails.TryWriteAsync(new()
        {{
            HttpContext = httpContext,
            Exception   = exception,
            ProblemDetails = new ProblemDetails
            {{
                Type    = "https://docs.yourapp.in/errors",
                Detail  = exception.Message,   // OK for dev; sanitise for prod
                Instance = httpContext.Request.Path
            }}
        }});
    }
}

public sealed class NotFoundException(string message) : Exception(message) {{ }}
""", "GlobalExceptionHandler.cs")}
{C(r"""
// BEFORE: unhandled exception leaks a stack trace
// GET /api/products/999  → 500 with HTML stack trace (bad!)

// AFTER: returns structured JSON
// {{
//   "type": "https://docs.yourapp.in/errors",
//   "title": "An error occurred while processing your request.",
//   "status": 500,
//   "detail": "Sequence contains no matching element",
//   "instance": "/api/products/999"
// }}
""", lang="json")}

<h3>3. Validation with FluentValidation + ProblemDetails</h3>
{C(r"""
// BEFORE: missing validation — negative price stored to DB
app.MapPost("/api/products", async (ProductDto dto, AppDb db, CancellationToken ct) =>
{{
    db.Products.Add(new Product {{ Name = dto.Name, Price = dto.Price }});
    await db.SaveChangesAsync(ct);
    return Results.Created();
}});

// AFTER: validate first, return 400 with field-level errors
app.MapPost("/api/products", async (
    ProductDto dto,
    IValidator<ProductDto> validator,
    AppDb db,
    CancellationToken ct) =>
{{
    var result = await validator.ValidateAsync(dto, ct);
    if (!result.IsValid)
        return Results.ValidationProblem(result.ToDictionary());

    db.Products.Add(new Product {{ Name = dto.Name, Price = dto.Price }});
    await db.SaveChangesAsync(ct);
    return Results.Created();
}}).RequireAuthorization();
""", "Fix2_Validation.cs")}

<h3>4. No PII in logs</h3>
{C(r"""
// BEFORE: Aadhaar number, email and phone in log line
logger.LogInformation("Login by {Email} with aadhaar {Aadhaar}", user.Email, user.AadhaarNo);

// AFTER: log identifiers only
logger.LogInformation("Login success. UserId={UserId}", user.Id);

// BEFORE: logging the full request body (may contain password)
app.Use(async (ctx, next) =>
{{
    ctx.Request.EnableBuffering();
    var body = await new StreamReader(ctx.Request.Body).ReadToEndAsync();
    logger.LogDebug("Request body: {{Body}}", body);   // ❌ PII leaks here
    ctx.Request.Body.Position = 0;
    await next();
}});

// AFTER: log only the route and method
app.Use(async (ctx, next) =>
{{
    logger.LogDebug("{{Method}} {{Path}}", ctx.Request.Method, ctx.Request.Path);
    await next();
}});
""", "Fix3_PII.cs")}

<h3>5. Health checks</h3>
{C(r"""
// Program.cs
builder.Services
    .AddHealthChecks()
    .AddSqlServer(                           // NuGet: AspNetCore.HealthChecks.SqlServer
        connectionString: builder.Configuration.GetConnectionString("Default")!,
        healthQuery: "SELECT 1",
        name: "sqlserver",
        failureStatus: HealthStatus.Degraded);

app.MapHealthChecks("/healthz/live",  new HealthCheckOptions {{ Predicate = _ => false }});  // liveness: just 200
app.MapHealthChecks("/healthz/ready", new HealthCheckOptions {{ ResponseWriter = WriteJsonResponse }});

static Task WriteJsonResponse(HttpContext ctx, HealthReport report)
{{
    ctx.Response.ContentType = "application/json";
    var json = System.Text.Json.JsonSerializer.Serialize(new
    {{
        status  = report.Status.ToString(),
        entries = report.Entries.ToDictionary(
            e => e.Key,
            e => new {{ status = e.Value.Status.ToString(), description = e.Value.Description }})
    }});
    return ctx.Response.WriteAsync(json);
}}
// GET /healthz/ready → {{ "status":"Healthy", "entries":{{ "sqlserver":{{ "status":"Healthy" }} }} }}
""", "Fix4_HealthChecks.cs")}

<h3>6. Rate limiting (built-in, .NET 7+)</h3>
{C(r"""
// Program.cs
using Microsoft.AspNetCore.RateLimiting;
using System.Threading.RateLimiting;

builder.Services.AddRateLimiter(opts =>
{{
    opts.AddFixedWindowLimiter("api", o =>
    {{
        o.Window            = TimeSpan.FromMinutes(1);
        o.PermitLimit       = 100;
        o.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
        o.QueueLimit        = 5;
    }});
    opts.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
}});

app.UseRateLimiter();

// Apply to a group (all /api/* routes)
var api = app.MapGroup("/api").RequireRateLimiting("api");

// BEFORE: no rate limiting — single IP can DDOS the catalog
// AFTER: 100 req/min per slot; 429 with Retry-After when exceeded
""", "Fix5_RateLimiting.cs")}

<h3>7. Paging cap and async + CancellationToken</h3>
{C(r"""
// BEFORE: caller can ask for 1 000 000 rows
app.MapGet("/api/products", (int page = 1, int pageSize = 20, AppDb db) =>
    db.Products.Skip((page - 1) * pageSize).Take(pageSize).ToList());

// AFTER: cap pageSize, full async, CancellationToken
const int MaxPage = 100;

app.MapGet("/api/products", async (
    int page, int pageSize, AppDb db, CancellationToken ct) =>
{{
    page     = Math.Max(1, page);
    pageSize = Math.Clamp(pageSize, 1, MaxPage);    // ✓ server-enforced cap

    var total = await db.Products.CountAsync(ct);
    var items = await db.Products
        .OrderBy(p => p.Id)
        .Skip((page - 1) * pageSize)
        .Take(pageSize)
        .Select(p => new ProductDto(p.Id, p.Name, p.Price))
        .ToListAsync(ct);                           // ✓ async + CancellationToken

    return Results.Ok(new {{ page, pageSize, total, items }});
}});
""", "Fix6_PagingAsync.cs")}

<h3>8. Connection-string hygiene</h3>
{C(r"""
// ❌ BEFORE: connection string hard-coded in appsettings.json (committed to git)
// appsettings.json
// {{ "ConnectionStrings": {{ "Default": "Server=prod.db.azure.com;User=sa;Password=P@ssw0rd!" }} }}

// ✓ AFTER option 1: developer machine — use user-secrets
// dotnet user-secrets init
// dotnet user-secrets set "ConnectionStrings:Default" "Server=.;Database=CatalogDev;Integrated Security=true"
// (stored outside the repo in %APPDATA%\Microsoft\UserSecrets\...)

// ✓ AFTER option 2: CI / production — environment variable
// ConnectionStrings__Default=Server=prod.db.azure.com;...   (double underscore = ':' in config)

// ✓ AFTER option 3: add to .gitignore
// appsettings.Development.json  (put the real string here and git-ignore this file)

// Program.cs — reading is the same either way
var connStr = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is not configured");
""", "Fix7_ConnString.cs")}

<h3>9. Migrations committed to source control</h3>
{C(r"""
# After every model change:
dotnet ef migrations add AddProductCategory          # generates Migrations/ folder files
git add Migrations/                                  # ✓ commit migration files
git commit -m "Add ProductCategory migration"

# CI can then apply pending migrations automatically:
dotnet ef database update                           # or in startup code with Migrate()

# BEFORE: migrations folder in .gitignore — team members run app and get different schemas
# AFTER: migrations committed — dotnet ef database update works for everyone
""", "Fix8_Migrations.sh", lang="bash")}
''',
["Returning 200 for created resources instead of 201 with a Location header.",
"Skipping <code>CancellationToken</code> on <code>SaveChangesAsync</code> calls — the connection stays open after the client disconnects.",
"Logging <code>dto.Password</code> or <code>dto.CardNumber</code> during validation.",
"No upper bound on pageSize — a single request can read millions of rows.",
"Storing connection strings in <code>appsettings.json</code> and committing them to a public GitHub repo."],
("40 min", [
    "Open the To-do API (Week 17). Run the checklist above and list every gap you find.",
    "Fix the top three gaps: add auth to all mutations, add paging cap, and add <code>CancellationToken</code> to every async call.",
    "Add a <code>/healthz/live</code> endpoint that returns 200 and a <code>/healthz/ready</code> endpoint that pings the database."]),
[("What does RequireAuthorization() do on a minimal API endpoint?","It applies the default authorization policy (authenticated user). Without it the endpoint is anonymous."),
("Why pass CancellationToken to SaveChangesAsync?","If the browser cancels the request mid-flight, EF Core cancels the in-progress database command, freeing the connection immediately instead of holding it until the query finishes."),
("What is a paging cap and why is it important?","A server-enforced upper limit on the page size requested by clients. Without it, a client can request all rows in one call, causing high DB load, slow responses and potential OOM.")],
[("Basic","What HTTP status code should a POST that creates a resource return?","201 Created, with a <code>Location</code> response header containing the URL of the new resource. Returning 200 is incorrect and breaks clients that inspect status codes."),
("Basic","What is ProblemDetails and why use it?","ProblemDetails is the RFC 7807 JSON error envelope: type, title, status, detail, instance. It gives every API a consistent error shape that clients can parse generically, replacing ad-hoc error strings."),
("Intermediate","How do health checks differ from a plain ping endpoint?","A health check actively probes dependencies (SQL Server, Redis, downstream APIs) and returns Healthy/Degraded/Unhealthy. A ping just checks the process is alive. Kubernetes uses both: liveness (ping) to restart crashed pods, readiness (dependency checks) to route traffic."),
("Intermediate","How does the built-in rate limiter work in .NET 7+?","Add <code>builder.Services.AddRateLimiter()</code>, configure a named policy (fixed window, sliding window, token bucket or concurrency), call <code>app.UseRateLimiter()</code>, and annotate routes with <code>.RequireRateLimiting(\"policyName\")</code>. The middleware returns 429 when the limit is exceeded."),
("Intermediate","What is the DPDP Act and how does it affect logging?","India's Digital Personal Data Protection Act (2023) restricts how personal data (names, emails, phone numbers, Aadhaar IDs) is collected and stored. Logging PII unnecessarily violates the purpose-limitation principle and exposes the organisation to penalties."),
("Intermediate","How do you store a connection string safely for a developer machine?","Run <code>dotnet user-secrets init</code> in the project, then <code>dotnet user-secrets set \"ConnectionStrings:Default\" \"...\"</code>. Secrets are stored outside the repo in the OS user profile; <code>builder.Configuration</code> reads them automatically in Development.")])

# ================= DAY 2  TUE =================
d2 = day(2, "TUE", "Postman collection for the Blog API",
"Build a complete, runnable Postman collection — environments, variables, login script, Bearer pre-request, pm.test checks — and run it with Newman in CI.",
[("Postman collection","A named group of saved HTTP requests, organized into folders, that can be run together."),
("Environment","A named set of key-value variables in Postman (e.g. Local, Staging) switched without changing requests."),
("Collection variable","A variable scoped to the collection, shared by all requests inside it."),
("Pre-request script","JavaScript that runs before a request fires; used to set a Bearer token from a collection variable."),
("Test script","JavaScript that runs after a response arrives; <code>pm.test()</code> and <code>pm.expect()</code> assert correctness."),
("Login script","A test script on the login request that extracts the JWT from the response and stores it in a variable."),
("pm.test","Postman's assertion function: <code>pm.test(\"name\", () => pm.expect(x).to.eql(y))</code>."),
("pm.environment.set","Sets an environment variable at runtime: <code>pm.environment.set(\"token\", jwt)</code>."),
("Collection runner","The Postman UI that executes all requests in order and shows pass/fail counts."),
("Newman","Postman's Node.js CLI runner; integrates Postman collections into CI pipelines."),
("CSRF","Cross-Site Request Forgery; Bearer tokens in Authorization headers are immune (browsers can't set custom headers cross-origin without CORS pre-flight)."),
("OAuth2 flow","For Postman, usually the Authorization Code + PKCE or Client Credentials flow; we use a simpler username/password login that returns a JWT.")],
["Keep Base URL in an environment variable so switching Local → Staging → Production changes one value.",
"The login request's test script is the keystone: it stores the token so every subsequent request can use it automatically.",
"Use <code>pm.response.to.have.status(201)</code> to assert status and <code>pm.response.json()</code> to inspect the body.",
"Pre-request scripts that read <code>pm.collectionVariables.get(\"token\")</code> and set the Authorization header run before EVERY request in the folder.",
"Newman exit codes: 0 = all tests pass, non-zero = failures — CI can gate on this.",
"Export the collection and environment as JSON and commit them to source control in a <code>tests/postman/</code> folder."],
f'''
<h3>1. Collection structure</h3>
<p>The Blog API (Week 19) has three resource areas. Mirror that in the collection:</p>
{C(r"""
Blog API (Collection)
├── 🌐 Environments: Local, Staging
├── Variables: baseUrl, token (empty at start), createdPostId, createdCommentId
│
├── Auth/
│   ├── POST Register
│   └── POST Login  ← test script stores token
│
├── Posts/
│   ├── GET  All Posts
│   ├── POST Create Post   ← stores createdPostId
│   ├── GET  Post By Id
│   ├── PUT  Update Post
│   └── DELETE Delete Post
│
└── Comments/
    ├── POST Create Comment  ← stores createdCommentId
    ├── GET  Comments for Post
    └── DELETE Delete Comment
""", "collection-layout.txt", lang="text")}

<h3>2. Environment — Local</h3>
{C(r"""
// In Postman: Environments → New → "Local"
// Variables:
// baseUrl  = http://localhost:5000     (initial + current)
// token    = (empty)                  (current set by login script)
//
// You can duplicate "Local" and change baseUrl to https://staging.yourapp.in
// for the "Staging" environment with zero request changes.
""", lang="text")}

<h3>3. POST Login — test script (auto-stores token)</h3>
{C(r"""
// Request: POST {{{{baseUrl}}}}/api/auth/login
// Body (raw JSON): {{ "email": "asha@example.com", "password": "Password@123" }}

// Tests tab (JavaScript):
pm.test("Login succeeds with 200", function () {{
    pm.response.to.have.status(200);
}});

pm.test("Response contains accessToken", function () {{
    const body = pm.response.json();
    pm.expect(body).to.have.property("accessToken");
    pm.expect(body.accessToken).to.be.a("string").and.not.empty;

    // Store for all subsequent requests
    pm.collectionVariables.set("token", body.accessToken);
}});
""", "Login_Tests.js", lang="javascript")}

<h3>4. Pre-request script on the Posts folder (auto-injects Bearer)</h3>
{C(r"""
// In Postman: click the "Posts" folder → Pre-request Script tab:
const token = pm.collectionVariables.get("token");
if (!token) {{
    throw new Error("token is empty — run Auth/Login first");
}}
pm.request.headers.add({{
    key: "Authorization",
    value: "Bearer " + token
}});
""", "Posts_PreRequest.js", lang="javascript")}

<h3>5. POST Create Post — full example</h3>
{C(r"""
// URL: POST {{{{baseUrl}}}}/api/posts
// Authorization: (inherited from folder pre-request)
// Headers: Content-Type: application/json
// Body:
// {{
//   "title": "EF Core Query Tips",
//   "body": "Use AsSplitQuery to avoid cartesian explosion in Include chains.",
//   "tags": ["efcore", "dotnet"]
// }}

// Tests tab:
pm.test("Post created with 201", function () {{
    pm.response.to.have.status(201);
}});

pm.test("Location header is present", function () {{
    pm.expect(pm.response.headers.get("Location")).to.include("/api/posts/");
}});

pm.test("Body contains post id", function () {{
    const body = pm.response.json();
    pm.expect(body).to.have.property("id").that.is.a("number");
    pm.expect(body.title).to.eql("EF Core Query Tips");

    pm.collectionVariables.set("createdPostId", body.id);
}});
""", "CreatePost_Tests.js", lang="javascript")}

<h3>6. GET All Posts — paging and schema check</h3>
{C(r"""
// URL: GET {{{{baseUrl}}}}/api/posts?page=1&pageSize=10

pm.test("Returns 200", () => pm.response.to.have.status(200));

pm.test("Response time under 500ms", () =>
    pm.expect(pm.response.responseTime).to.be.below(500));

pm.test("PagedResult schema", function () {{
    const body = pm.response.json();
    pm.expect(body).to.have.all.keys("items", "page", "pageSize", "total");
    pm.expect(body.items).to.be.an("array");
    pm.expect(body.page).to.eql(1);
    pm.expect(body.pageSize).to.eql(10);
}});
""", "GetPosts_Tests.js", lang="javascript")}

<h3>7. DELETE — 204 and idempotency check</h3>
{C(r"""
// URL: DELETE {{{{baseUrl}}}}/api/posts/{{{{createdPostId}}}}

pm.test("Delete returns 204 No Content", function () {{
    pm.response.to.have.status(204);
    pm.expect(pm.response.text()).to.be.empty;
}});

// Optional second run: check idempotency (should return 404)
// pm.test("Second delete returns 404", function () {{
//     pm.response.to.have.status(404);
// }});
""", "DeletePost_Tests.js", lang="javascript")}

<h3>8. Trimmed collection JSON (structure only)</h3>
{C(r"""
{{
  "info": {{
    "name": "Blog API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  }},
  "variable": [
    {{ "key": "baseUrl",          "value": "http://localhost:5000" }},
    {{ "key": "token",            "value": "" }},
    {{ "key": "createdPostId",    "value": "" }},
    {{ "key": "createdCommentId", "value": "" }}
  ],
  "item": [
    {{
      "name": "Auth",
      "item": [
        {{
          "name": "Login",
          "request": {{
            "method": "POST",
            "url": "{{{{baseUrl}}}}/api/auth/login",
            "header": [{{ "key": "Content-Type", "value": "application/json" }}],
            "body": {{
              "mode": "raw",
              "raw": "{{ \\"email\\": \\"asha@example.com\\", \\"password\\": \\"Password@123\\" }}"
            }}
          }},
          "event": [{{
            "listen": "test",
            "script": {{
              "exec": [
                "pm.test('200 OK', () => pm.response.to.have.status(200));",
                "pm.collectionVariables.set('token', pm.response.json().accessToken);"
              ]
            }}
          }}]
        }}
      ]
    }},
    {{
      "name": "Posts",
      "event": [{{
        "listen": "prerequest",
        "script": {{
          "exec": [
            "pm.request.headers.add({{ key: 'Authorization', value: 'Bearer ' + pm.collectionVariables.get('token') }});"
          ]
        }}
      }}],
      "item": [
        {{ "name": "GET All Posts",   "request": {{ "method": "GET",    "url": "{{{{baseUrl}}}}/api/posts" }} }},
        {{ "name": "POST Create Post","request": {{ "method": "POST",   "url": "{{{{baseUrl}}}}/api/posts" }} }},
        {{ "name": "DELETE Post",     "request": {{ "method": "DELETE", "url": "{{{{baseUrl}}}}/api/posts/{{{{createdPostId}}}}" }} }}
      ]
    }}
  ]
}}
""", "blog-api-collection.json", lang="json")}

<h3>9. Running with Newman in CI</h3>
{C(r"""
# Install Newman globally (Node.js required)
npm install -g newman

# Run the collection against Local environment (all tests must pass)
newman run tests/postman/blog-api-collection.json \\
       --environment tests/postman/local.env.json \\
       --reporters cli,junit \\
       --reporter-junit-export results/newman-report.xml

# Newman exits with code 1 on test failures, failing the CI step.

# GitHub Actions snippet
# .github/workflows/api-tests.yml
# - name: Start API
#   run: dotnet run --project src/Blog.Api &
# - name: Wait for API
#   run: sleep 5
# - name: Run Postman tests
#   run: newman run tests/postman/blog-api-collection.json -e tests/postman/local.env.json
""", "run-newman.sh", lang="bash")}
{tip("Export both the collection and the environment (without real passwords) to <code>tests/postman/</code> in your repo. Use a CI secret for the actual password, overriding with <code>--env-var \"password=$BLOG_TEST_PASSWORD\"</code>.")}
''',
["Storing the real staging password in the environment JSON committed to git — use CI secrets.",
"Not running Login before POST/PUT/DELETE requests in the collection runner — set the right run order.",
"Using global variables instead of collection variables — collection variables are scoped to the collection and don't leak into other collections.",
"Forgetting <code>pm.collectionVariables.set()</code> in the Login test; every subsequent request gets a 401.",
"Testing only the happy path; always add a test for the 401 (no token) and 404 (missing id) cases."],
("40 min", [
    "Export the Blog API Postman collection to <code>tests/postman/blog-api.json</code> and the Local environment to <code>tests/postman/local.env.json</code>.",
    "Add a folder-level pre-request script on the Posts and Comments folders that injects the Bearer token.",
    "Run the collection with Newman; ensure all tests pass before committing the JSON files."]),
[("How does the login script share the token with subsequent requests?","It calls <code>pm.collectionVariables.set(\"token\", body.accessToken)</code>. Collection variables are readable by pre-request and test scripts in every request inside that collection."),
("Why use a folder pre-request script instead of adding Authorization to every request?","DRY: one script on the folder applies to all requests inside it. If the header name or format changes, you update one place."),
("What does Newman exit code 1 mean in CI?","At least one <code>pm.test()</code> assertion failed, or the request errored. CI treats non-zero as a build failure, preventing a broken API from being deployed.")],
[("Basic","What is a Postman environment and why is it useful?","A named set of variables (baseUrl, credentials) that you switch as a unit. Switching from Local to Staging changes all base URLs in one click without editing any request."),
("Basic","What is a collection runner?","Postman's built-in tool that executes all requests in a collection in order, running pre-request and test scripts, and showing a pass/fail summary. Newman is the headless CLI version."),
("Intermediate","How do you chain requests so each one uses data created by the previous?","Use test scripts to store IDs in collection variables (<code>pm.collectionVariables.set(\"postId\", body.id)</code>), then reference them in subsequent request URLs as <code>{{{{postId}}}}</code>."),
("Intermediate","How do you test a 401 Unauthorized case in Postman?","Duplicate the request, remove the Authorization header, and add a test: <code>pm.test('No token = 401', () => pm.response.to.have.status(401))</code>. Put it in an 'Unhappy path' folder."),
("Intermediate","How do you integrate Postman tests into a GitHub Actions pipeline?","Commit the collection and environment JSON to the repo, install Newman in the workflow (<code>npm i -g newman</code>), start the API, then run <code>newman run collection.json -e env.json</code>. Newman exits non-zero on failure, failing the step.")])

# ================= DAY 3  WED =================
d3 = day(3, "WED", "Fix one slow query end to end",
"Diagnose and fix a slow catalog list endpoint in three steps — capture the problem, understand the cause, apply the fix — using EF Core and SQL Server query tools.",
[("Execution plan","A tree of operators SQL Server uses to satisfy a query; shows cost, row estimates, actual rows, warnings."),
("Index seek","Reading only the matching rows via a B-tree lookup — fast."),
("Index scan","Reading every row in an index — slow on large tables."),
("Clustered index scan","Reading every row in the entire table (worst case)."),
("Leading wildcard","A LIKE pattern starting with <code>%</code>: e.g. <code>LIKE '%phone'</code> cannot use a B-tree index."),
("Missing index hint","A yellow warning in an execution plan suggesting a covering index."),
("Cartesian Include","An EF Core <code>.Include()</code> that generates a JOIN, multiplying rows; fixed with <code>.AsSplitQuery()</code>."),
("AsSplitQuery","EF Core 5+ option: issues one SELECT per Include instead of a JOIN, avoiding row multiplication."),
("Covering index","An index that contains all columns the query needs so SQL Server never visits the data page."),
("N+1","One query to get N parents then N more queries to get each parent's children — fixed by Include or AsSplitQuery."),
("SET STATISTICS IO ON","T-SQL command that reports logical reads per table — the fastest way to compare query cost before and after a fix."),
("Query Store","SQL Server 2016+ feature that captures query plans and execution stats automatically, with no instrumentation code needed.")],
["Use <code>LogTo(Console.WriteLine, LogLevel.Information)</code> in <code>DbContext</code> options during development to see the generated SQL.",
"Always compare logical reads (from <code>SET STATISTICS IO ON</code>), not wall-clock time, to get a reproducible measurement.",
"Add an index in a migration (<code>HasIndex</code> in EF Core) so it is tracked in source control, not applied ad hoc.",
"Switching from a leading wildcard to a full-text search or a computed persisted column is the proper long-term fix.",
"<code>AsSplitQuery()</code> trades fewer rows for more round trips; profile both to pick the right one.",
"Keep the runbook in <code>docs/runbooks/slow-query.md</code> in the repo so the fix is repeatable."],
f'''
<h3>Scenario — Catalog list is slow</h3>
<p>The product catalog endpoint (<code>GET /api/products?search=&amp;categoryId=&amp;page=1&amp;pageSize=20</code>) works fine with 100 rows but takes several seconds with 50 000 products once categories and reviews are included.</p>

<h3>Step 1 — Capture the problem</h3>
<h4>1a. Enable EF Core SQL logging</h4>
{C(r"""
// AppDbContext.cs (development only)
protected override void OnConfiguring(DbContextOptionsBuilder opts)
{{
    if (!opts.IsConfigured)
        opts.UseSqlServer(connectionString)
            .LogTo(Console.WriteLine, LogLevel.Information)   // prints SQL to console
            .EnableSensitiveDataLogging();                     // shows parameter values
}}
""", "AppDbContext.cs")}
<h4>1b. The generated SQL (captured from console output)</h4>
{C(r"""
-- Generated by EF Core for the BEFORE query
SELECT p.Id, p.Name, p.Price, p.Description,
       c.Id, c.Name,
       r.Id, r.Rating, r.Comment
FROM   Products p
LEFT JOIN Categories c ON c.Id = p.CategoryId
LEFT JOIN Reviews    r ON r.ProductId = p.Id
WHERE  p.Name LIKE '%' + @search + '%'   -- leading wildcard: no index possible
ORDER  BY p.Id
OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY;

-- SET STATISTICS IO ON shows:
-- Table 'Products'.  Scan count 1, logical reads 1240.
-- Table 'Reviews'.   Scan count 1, logical reads 8730.   ← row multiplication
""", "slow-query-captured.sql", lang="sql")}
<h4>1c. Execution plan warning</h4>
{C(r"""
-- Paste the query into SSMS (Ctrl+M for actual execution plan)
-- You will see:
-- ⚠ Missing Index: CREATE NONCLUSTERED INDEX [IX_Products_Name] ON [Products] ([Name])
-- ⚠ The JOIN to Reviews produces 50 000 × avg(reviews per product) rows before OFFSET/FETCH
""", lang="text")}

<h3>Step 2 — Diagnose: three separate problems</h3>
{table(["#","Problem","Root cause","Impact"],[
["1","Leading wildcard","<code>LIKE '%' + @search + '%'</code> forces a full table scan regardless of indexes","All 50 000 rows scanned every request"],
["2","Missing index on Products.Name","No index to even partially help the WHERE clause","Clustered index scan"],
["3","Cartesian Include","<code>.Include(p => p.Reviews)</code> as a JOIN multiplies rows in the result set","50 000 products × 5 reviews = 250 000 rows sent to app"]])}

<h3>Step 3 — Fix</h3>
<h4>Fix A — Replace leading wildcard with a trailing anchor (or full-text)</h4>
{C(r"""
// BEFORE (EF Core query builder)
var query = db.Products.AsQueryable();
if (!string.IsNullOrWhiteSpace(search))
    query = query.Where(p => p.Name.Contains(search));       // generates LIKE '%search%'

// AFTER option 1: trailing anchor only (works for "starts with" searches)
if (!string.IsNullOrWhiteSpace(search))
    query = query.Where(p => p.Name.StartsWith(search));     // generates LIKE 'search%' — index-sargable
                                                              // ✓ can use an index on Name

// AFTER option 2: full-text search (for real "contains" need)
// Requires enabling full-text on the column:
// ALTER TABLE Products ADD FULLTEXT INDEX ix_ft_name ON Name;
// Then use a raw SQL interpolation or EF Core FTS extension.
""", "Fix_A_Search.cs")}

<h4>Fix B — Add a covering index via EF Core migration</h4>
{C(r"""
// In the Product entity configuration (ProductConfiguration.cs or OnModelCreating):
modelBuilder.Entity<Product>()
    .HasIndex(p => p.Name)                   // creates IX_Products_Name
    .HasDatabaseName("IX_Products_Name");

// If the query also filters by CategoryId:
modelBuilder.Entity<Product>()
    .HasIndex(p => new {{ p.CategoryId, p.Name }}); // composite: seek on CategoryId, then Name

// Generate and commit the migration:
// dotnet ef migrations add AddProductNameIndex
""", "Fix_B_Index.cs")}
{C(r"""
-- Migration SQL (generated)
CREATE NONCLUSTERED INDEX [IX_Products_Name]
    ON [Products] ([Name] ASC)
    INCLUDE ([Id], [Price], [CategoryId]);   -- covering: SELECT doesn't need to visit the data page
""", "IX_Products_Name.sql", lang="sql")}

<h4>Fix C — Replace cartesian Include with AsSplitQuery</h4>
{C(r"""
// BEFORE: one large JOIN — row multiplication
var products = await db.Products
    .Include(p => p.Category)
    .Include(p => p.Reviews)              // ← produces 50k × n rows
    .Where(p => p.Name.StartsWith(search))
    .OrderBy(p => p.Id)
    .Skip((page - 1) * pageSize)
    .Take(pageSize)
    .ToListAsync(ct);

// AFTER: AsSplitQuery — EF Core issues three separate SELECTs
var products = await db.Products
    .Include(p => p.Category)
    .Include(p => p.Reviews)
    .AsSplitQuery()                        // ✓ three queries instead of one big JOIN
    .Where(p => p.Name.StartsWith(search))
    .OrderBy(p => p.Id)
    .Skip((page - 1) * pageSize)
    .Take(pageSize)
    .ToListAsync(ct);

// Generated SQL (three round trips, all fast):
// SELECT TOP(20) p.Id, p.Name, p.Price, p.CategoryId FROM Products AS p
//   WHERE p.Name LIKE @search + '%'
//   ORDER BY p.Id OFFSET 0 ROWS;
//
// SELECT c.Id, c.Name FROM Categories AS c
//   WHERE c.Id IN (101, 102, ...);    -- the 20 category ids from above
//
// SELECT r.Id, r.Rating, r.ProductId FROM Reviews AS r
//   WHERE r.ProductId IN (1, 2, ...); -- the 20 product ids
""", "Fix_C_SplitQuery.cs")}

<h3>Verify — measure before and after</h3>
{C(r"""
-- Run both versions in SSMS with SET STATISTICS IO ON
SET STATISTICS IO ON;
SET STATISTICS TIME ON;

-- BEFORE (leading wildcard + cartesian JOIN):
-- Table 'Products'. Scan count 1, logical reads 1240.
-- Table 'Reviews'.  Scan count 1, logical reads 8730.
-- SQL Server Execution Times: CPU time = 450 ms,  elapsed time = 612 ms.

-- AFTER (trailing LIKE + index + split query):
-- Table 'Products'. Scan count 1, logical reads  18.    ← 69× fewer reads
-- Table 'Reviews'.  Scan count 1, logical reads  42.    ← 200× fewer reads
-- SQL Server Execution Times: CPU time = 3 ms,  elapsed time = 8 ms.
""", "verify-stats.sql", lang="sql")}
{tip("Add <code>AsSplitQuery()</code> as a default on the entire context if most of your queries include multiple collections: <code>opts.UseSqlServer(cs, o => o.UseQuerySplittingBehavior(QuerySplittingBehavior.SplitQuery))</code>.")}
{warn("AsSplitQuery sends multiple round trips; under high latency (a distant database) or inside a transaction with snapshot isolation, single-query mode may be faster. Profile both.", "Trade-off")}
''',
["Adding an index in SSMS directly without a migration — the fix disappears on a fresh deploy.",
"Using <code>LIKE '%term%'</code> and expecting an index to help — it cannot.",
"Adding too many indexes (every index slows writes); only add what a captured slow query asks for.",
"Applying <code>AsSplitQuery</code> globally when you have queries that return single-row-per-parent results — the extra round trips add overhead for simple queries.",
"Not re-running <code>SET STATISTICS IO ON</code> after the fix to confirm the improvement."],
("40 min", [
    "Open the Product Catalog API (Week 18). Enable EF Core SQL logging and call <code>GET /api/products?search=ph</code>. Copy the SQL to SSMS.",
    "Run <code>SET STATISTICS IO ON</code> to measure logical reads before any change. Paste the execution plan warning into a comment in the code.",
    "Apply all three fixes (StartsWith, HasIndex migration, AsSplitQuery), regenerate logical-read stats, and record the improvement in a <code>docs/runbooks/catalog-slow-query.md</code> file."]),
[("What is a leading wildcard and why is it slow?","A LIKE pattern that starts with <code>%</code>, e.g. <code>LIKE '%phone'</code>. SQL Server cannot use a B-tree index to find matching rows because the index is ordered by the first character, so it must scan every row."),
("What does AsSplitQuery do?","Instead of one JOIN that multiplies rows, EF Core issues one SELECT per Include, then matches the results in memory. This avoids the cartesian explosion but adds extra database round trips."),
("How do you add an index via EF Core?","Call <code>.HasIndex(e => e.Property)</code> in entity configuration, then run <code>dotnet ef migrations add &lt;Name&gt;</code> to generate and commit the migration.")],
[("Basic","What is a SQL execution plan and how do you read it?","A tree of operators (scans, seeks, joins, sorts) SQL Server uses to run a query. Each operator shows estimated and actual row counts. Yellow warnings highlight missing indexes or row-count mismatches. In SSMS, press Ctrl+M to capture the actual plan."),
("Basic","Explain the difference between an index seek and an index scan.","A seek jumps to the first matching row via the B-tree and reads only the matching range (fast). A scan reads every row in the index from start to end (slow on large tables). WHERE clauses with leading wildcards force a scan."),
("Intermediate","What is the cartesian explosion problem in EF Core Include?","When you .Include() two collections via JOIN, SQL Server multiplies the rows: 100 orders × 5 items × 3 events = 1500 rows returned for 100 orders. AsSplitQuery or separate queries avoid this."),
("Intermediate","How does a covering index improve query performance?","A covering index includes all columns needed by the query (in INCLUDE) so SQL Server reads the index leaf pages without visiting the data page (clustered index). This reduces logical reads significantly."),
("Advanced","When would you NOT use AsSplitQuery?","When the extra round trips cost more than the row-multiplication saving: very low-latency databases, queries with only one Include, or inside a serialisable transaction where split queries can read inconsistent snapshots across the two SELECTs.")])

# ================= DAY 4  THU =================
d4 = day(4, "THU", "Interview prep: explain aloud",
"Practise 2-minute verbal answers for the six most common .NET backend interview topics; know what interviewers listen for and what wrong answers sound like.",
[("DI lifetime","The scope a registered service lives in: Transient (new every injection), Scoped (once per HTTP request), Singleton (once per app lifetime)."),
("Service locator","Anti-pattern: calling <code>serviceProvider.GetService&lt;T&gt;()</code> inside a class instead of injecting via constructor."),
("Middleware pipeline","An ordered chain of RequestDelegate components; each calls next() to pass the request forward and can inspect/modify request and response."),
("Short-circuiting","Middleware that returns a response without calling next() (e.g. auth failure)."),
("JWT","JSON Web Token: header.payload.signature, signed with a secret or RSA key; the server validates the signature instead of storing session state."),
("Claims","Key-value pairs inside a JWT payload (sub, email, roles); extracted automatically by ASP.NET Core's auth middleware."),
("Clustered index","The table's physical sort order; SQL Server stores rows on the leaf level. Only one per table; usually the primary key."),
("Non-clustered index","A separate B-tree with key columns pointing back to the clustered key; a table can have many."),
("Change tracking","EF Core's internal snapshot of entity state (Added, Modified, Unchanged, Deleted, Detached); <code>SaveChanges</code> generates SQL for changed entities."),
("AsNoTracking","Skips change tracking for a query; faster and uses less memory for read-only results."),
("N+1 query","Fetching N parents then N individual child queries instead of a single JOIN or Include.")],
["Answer every question out loud before reading the model answer.",
"Time each answer — 2 minutes is the target; under 90 seconds is thin, over 3 minutes loses the interviewer.",
"The 'wrong answer' patterns below are what nervous candidates say; recognise them in your own draft answers.",
"Draw a diagram on a whiteboard or iPad while you explain — it shows communication skill.",
"Close the page, re-explain the topic 10 minutes later; the second attempt reveals what you don't own yet."],
f'''
<h3>How to use this day</h3>
<ol>
<li>Read the topic title and listening points.</li>
<li>Close the page; stand up; speak for 2 minutes to a camera or a friend.</li>
<li>Open the model answer and compare.</li>
<li>Identify one thing you said wrong or omitted and re-explain that part.</li>
</ol>

<h3>Topic 1 — DI lifetimes</h3>
{table(["Listening for","Wrong answer sounds like"],[
["Names all three lifetimes correctly","Confuses Scoped and Singleton"],
["Explains the captive dependency bug","Says 'just use Singleton, it's faster'"],
["Gives a concrete example for each","Abstract: 'Transient is for things you need once'"]])}
{C(r"""
// Model answer (spoken):
// "There are three lifetimes in .NET DI.
//  Transient: a new instance is created every time it's injected — good for
//  lightweight stateless services like a formatter or a calculator.
//  Scoped: one instance per HTTP request — the right choice for DbContext,
//  because one context per request keeps change tracking correct and avoids
//  threading problems.
//  Singleton: one instance for the whole application lifetime — good for
//  caches, configuration, or HttpClient factories.
//
//  The 'captive dependency' trap: if a Singleton injects a Scoped service,
//  the Scoped instance lives as long as the Singleton — the whole app — which
//  means it may hold a stale DbContext. ASP.NET Core detects this in Development
//  and throws an InvalidOperationException. Fix: inject IServiceScopeFactory
//  and create a scope manually."

// Code interviewers often show:
var svc = new SomeService(new ScopedService());  // ❌ captive dependency
// vs.
public class SomeService(IServiceScopeFactory factory) {{
    public void DoWork() {{
        using var scope = factory.CreateScope();
        var dep = scope.ServiceProvider.GetRequiredService<ScopedService>();
    }}
}}
""", "DI_Lifetimes.cs")}

<h3>Topic 2 — Middleware order</h3>
{table(["Listening for","Wrong answer sounds like"],[
["Knows order matters","'You can put them anywhere'"],
["Exception handler goes first","'Auth goes first'"],
["Explains short-circuiting","Only lists middleware names without explaining flow"]])}
{C(r"""
// Model answer (spoken):
// "Middleware runs in the order it's registered in Program.cs, and the response
//  travels back through it in reverse — like an onion. Order matters a lot.
//
//  The exception handler must come first so it can catch exceptions thrown by
//  any later middleware.
//  HTTPS redirection and HSTS must come before routing so they fire on every request.
//  Authentication reads the JWT and sets HttpContext.User.
//  Authorization must come after authentication — it reads User.
//  Rate limiting sits before the endpoint so it can short-circuit with 429 without
//  executing any endpoint code.
//
//  Short-circuiting: auth middleware calls Response.StatusCode = 401 and returns
//  without calling next(), so the endpoint never runs."

// Canonical order:
// app.UseExceptionHandler();
// app.UseHsts(); app.UseHttpsRedirection();
// app.UseRouting();
// app.UseCors();
// app.UseAuthentication();
// app.UseAuthorization();
// app.UseRateLimiter();
// app.MapControllers() / app.MapEndpoints();
""", "Middleware_Order.cs")}

<h3>Topic 3 — JWT end to end</h3>
{table(["Listening for","Wrong answer sounds like"],[
["Describes three parts: header, payload, signature","'It's encrypted' (JWTs are signed, not encrypted by default)"],
["Server validates signature, not a session store","'The server looks up the token in a database'"],
["Knows refresh token pattern","Blank look when asked about token expiry"]])}
{C(r"""
// Model answer (spoken):
// "A JWT is a Base64Url-encoded string in three dot-separated parts.
//  The header says the algorithm — usually HS256 (symmetric) or RS256 (asymmetric).
//  The payload contains claims: sub (userId), email, roles, exp (expiry).
//  The signature is computed by HMAC-SHA256(base64(header)+'.'+base64(payload), secret).
//
//  At login, the server generates and signs the JWT and returns it to the client.
//  On every subsequent request, the client puts it in Authorization: Bearer <token>.
//  The server verifies the signature (no DB call needed) and reads the claims.
//
//  Because JWTs are stateless, you can't 'invalidate' one before it expires.
//  The standard pattern: short-lived access token (15 min) + long-lived refresh token
//  stored in an HttpOnly cookie. The client exchanges the refresh token for a new
//  access token when the access token expires."

// ASP.NET Core setup (from Week 20):
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(opts => {{
        opts.TokenValidationParameters = new TokenValidationParameters
        {{
            ValidateIssuer           = true,
            ValidIssuer              = "yourapp.in",
            ValidateAudience         = true,
            ValidAudience            = "yourapp.in/api",
            ValidateLifetime         = true,
            ValidateIssuerSigningKey = true,
            IssuerSigningKey         = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(config["Jwt:Key"]!))
        }};
    }});
""", "JWT_Setup.cs")}

<h3>Topic 4 — Clustered vs non-clustered index</h3>
{table(["Listening for","Wrong answer sounds like"],[
["One clustered per table (usually PK)","'You can have multiple clustered indexes'"],
["Clustered stores data at leaf level","'Clustered is just faster'"],
["Non-clustered RID or key lookup","Can't explain what a 'lookup' is"]])}
{C(r"""
// Model answer (spoken):
// "A clustered index determines the physical storage order of rows in the table.
//  SQL Server stores the actual row data at the leaf level of the B-tree.
//  Every table can have exactly one clustered index — usually the primary key.
//
//  A non-clustered index is a separate B-tree containing the indexed columns,
//  with a pointer (the clustered key value) back to the row.
//  When a query uses a non-clustered index but needs columns not in that index,
//  SQL Server does a 'Key Lookup' — an extra read on the clustered index.
//  You eliminate this with a covering index by adding INCLUDE columns.
//
//  Composite example: CREATE INDEX IX_Orders_CustomerId
//    ON Orders (CustomerId) INCLUDE (OrderDate, Total)
//  — a query filtering on CustomerId and selecting OrderDate, Total never needs
//    to visit the data page."

-- Interview question that follows:
-- "If a table has no clustered index, what is it called?"
-- Answer: a heap. Rows are in insertion order; every non-clustered index lookup
-- adds a RID (row-id) lookup which is essentially random I/O.
""", lang="sql")}

<h3>Topic 5 — EF Core change tracking</h3>
{table(["Listening for","Wrong answer sounds like"],[
["Entity states: Added, Modified, Unchanged, Deleted, Detached","Only knows 'it tracks changes'"],
["AsNoTracking for read-only queries","'Always use tracking'"],
["SaveChanges generates SQL from tracked changes","'SaveChanges just saves'"]])}
{C(r"""
// Model answer (spoken):
// "When you query with EF Core, the returned entities are added to the DbContext's
//  change tracker with state Unchanged. If you modify a property, EF marks the
//  entity Modified and remembers the original values. SaveChanges() compares
//  current vs original, generates an UPDATE with only the changed columns,
//  and executes it in a transaction.
//  New entities added with db.Add() get state Added; db.Remove() marks them Deleted.
//  Detached means the context doesn't know about the entity.
//
//  For read-only queries — reports, GET responses — use AsNoTracking() or
//  AsNoTrackingWithIdentityResolution(). EF skips building the snapshot,
//  which is faster and uses less memory, especially important for large result sets."

var products = await db.Products.AsNoTracking().ToListAsync(ct);  // ✓ read-only GET
var product   = await db.Products.FindAsync(id);                  // ✓ tracked for update
product!.Price = 1299m;                                           // Modified state
await db.SaveChangesAsync(ct);                                    // UPDATE Products SET Price=1299 WHERE Id=@id
""", "ChangeTracking.cs")}

<h3>Topic 6 — N+1 query problem</h3>
{table(["Listening for","Wrong answer sounds like"],[
["Describes 1 + N queries pattern","Thinks N+1 is unavoidable"],
["Knows Include and AsSplitQuery","'Just load lazily'"],
["Can quantify the impact at scale","Vague about why it matters"]])}
{C(r"""
// Model answer (spoken):
// "N+1 is when your code issues one query to get N parents, then one query per parent
//  to get its children — N+1 total database round trips.
//  With 500 orders you send 501 queries; with lazy loading enabled in EF Core
//  this happens silently and can easily kill a production API under load.
//
//  The fix is eager loading with .Include() (single JOIN) or .AsSplitQuery()
//  (separate SELECT per collection). AsSplitQuery avoids row multiplication
//  when there are multiple collections.
//
//  You can detect N+1 in development with EF Core logging: watch for the same
//  SQL repeated with different parameter values."

// BEFORE: N+1 (lazy loading or loop)
var orders = await db.Orders.ToListAsync(ct);       // 1 query
foreach (var o in orders)
    Console.WriteLine(o.Customer.Name);             // N queries — lazy load per order

// AFTER: eager load
var orders = await db.Orders.Include(o => o.Customer).ToListAsync(ct);  // 1 query
""", "N1_Fix.cs")}
''',
["Saying 'Scoped is for database connections' instead of 'one per HTTP request' — the interviewer expects the DI lifecycle definition.",
"Saying JWTs are encrypted — they are signed (integrity), not encrypted (confidentiality) by default.",
"Saying 'you can have multiple clustered indexes' — you can't.",
"Saying 'AddNoTracking' instead of 'AsNoTracking' — small typo that signals you haven't used EF Core hands-on.",
"Describing N+1 without quantifying it — always mention the number of round trips (501 for 500 orders)."],
("30 min", [
    "Pick any two topics above. Set a 2-minute timer and explain them out loud to a camera. Play back and note one gap.",
    "For the DI lifetime topic: open the Blog API (Week 19) and find one Singleton, one Scoped and one Transient service. Justify each registration.",
    "Draw the JWT flow on paper (or a whiteboard tool): login → server signs → client stores → request → server validates → claims."]),
[("What is the captive dependency problem?","A Singleton injecting a Scoped service. The Scoped instance is kept alive for the Singleton's lifetime, holding stale state. Fix: inject IServiceScopeFactory."),
("Why can't you invalidate a JWT before it expires?","JWTs are stateless — the server validates the signature only, without looking anything up. To invalidate early, you need a token blacklist in a cache (Redis), which re-introduces server state."),
("What is AsNoTracking?","An EF Core query option that skips the change-tracking snapshot, making read-only queries faster and lighter on memory.")],
[("Basic","What are the three DI service lifetimes in ASP.NET Core?","Transient: new instance every injection. Scoped: one instance per HTTP request (default for DbContext). Singleton: one instance for the whole application. Registering a Scoped service inside a Singleton is a captive dependency — ASP.NET Core throws at startup in Development."),
("Basic","What are the three parts of a JWT?","Header (algorithm and type), payload (claims: sub, email, roles, exp), and signature (HMAC or RSA of base64(header).base64(payload)). They are Base64Url-encoded and dot-separated. JWTs are signed for integrity, not encrypted by default."),
("Intermediate","Describe the correct middleware order for an ASP.NET Core API.","Exception handler → HTTPS redirection → routing → CORS → authentication → authorization → rate limiting → endpoints. Auth must come after routing (which provides the metadata the auth middleware reads). Authorization must come after authentication."),
("Intermediate","Explain EF Core change tracking and when to turn it off.","EF Core snapshots entities when queried; on SaveChanges it compares current state to the snapshot and generates minimal SQL (only changed columns). Turn it off with AsNoTracking() for read-only operations — saves memory and CPU with no functional downside."),
("Intermediate","What is the N+1 problem and how do you fix it?","Loading N parents with one query then issuing one query per parent to load children — N+1 total queries. Fix with .Include() (single JOIN) or .AsSplitQuery() (separate SELECT per collection, avoids row multiplication). Detect it via EF Core logging."),
("Advanced","How would you invalidate a JWT before it expires?","Use a short access-token lifetime (15 min) and a revocation store (Redis or a DB table) of invalidated jti claim values. The auth middleware checks the store after validating the signature. This trades some statelessness for the ability to log out users instantly — a deliberate architectural decision.")])

# ================= DAY 5  FRI =================
d5 = day(5, "FRI", "Refactor the weakest repo",
"Decide which of the Week 17–21 projects needs the most structure, then apply the Catalog/Blog layered shape to it without breaking any endpoints.",
[("Layered architecture","Presentation (API) → Application (services / use cases) → Domain (entities, value objects) → Infrastructure (EF Core, email, external APIs)."),
("Dependency inversion","Depend on interfaces, not concrete types. Infrastructure implements interfaces defined in Application or Domain."),
("Leaky abstraction","Implementation details bleeding through a layer boundary (e.g. <code>IQueryable&lt;T&gt;</code> leaking from the repository into the service layer)."),
("CQRS (simple)","Separating read models (queries, DTOs) from write models (commands, domain entities). Not necessarily event-sourced."),
("Feature folder","Grouping by feature (Products/, Orders/) rather than by type (Controllers/, Services/, Repositories/)."),
("Anemic domain model","A domain object with only properties and no behaviour — all logic lives in service classes."),
("Service layer","Application services that orchestrate domain objects and repositories without containing business rules."),
("DTO","Data Transfer Object: a flat, serialisable object returned from or accepted by the API layer, with no EF Core navigation properties."),
("AutoMapper / Mapster","Libraries that project domain entities to DTOs by convention; we map manually in Phase 2 for clarity."),
("Contract test","A test that verifies the API's JSON shape hasn't changed, breaking clients.")],
["The To-do API (Week 17) is usually the weakest: single-file Program.cs with no layers.",
"Refactoring means zero endpoint changes — the HTTP contract stays identical; only internal structure changes.",
"Start by extracting an interface; let the compiler tell you what else needs moving.",
"Keep each commit small and green: extract interface → move implementation → inject → move to Infrastructure."],
f'''
<h3>Decision framework</h3>
{table(["Question","Score 1 (bad)","Score 3 (fine)","Score 5 (good)"],[
["Layers separated?","Everything in Program.cs","Controllers + 1 service class","Domain / Application / Infrastructure projects"],
["DTOs used?","EF entities returned directly","Some DTOs","All API responses are DTOs"],
["Interfaces?","No interfaces; all concrete","1–2 interfaces","All services injected by interface"],
["Tests?","None","1 happy-path test","Repositories and services unit-tested"],
["Auth on mutations?","None","Most mutations protected","All mutations protected, 401/403 tested"],
["Migrations committed?","DB scripts only","Generated but not committed","Generated, committed, CI applies them"]])}
<p>Score each of your Week 17–21 projects. The lowest total is the one to refactor today.</p>
{C(r"""
// Typical result: To-do API (Week 17) scores 1–2 on most rows.
// It is usually a flat Program.cs with inline EF queries, no DTOs, no interfaces.
""", lang="text")}

<h3>Target shape (from Catalog / Blog API)</h3>
{C(r"""
TodoApi/
├── TodoApi.Domain/
│   ├── Entities/
│   │   └── TodoItem.cs
│   └── Interfaces/
│       └── ITodoRepository.cs
│
├── TodoApi.Application/
│   ├── DTOs/
│   │   ├── TodoItemDto.cs
│   │   └── CreateTodoRequest.cs
│   └── Services/
│       └── TodoService.cs   (ITodoService)
│
├── TodoApi.Infrastructure/
│   ├── Persistence/
│   │   ├── AppDbContext.cs
│   │   └── TodoRepository.cs   (implements ITodoRepository)
│   └── DependencyInjection.cs
│
└── TodoApi.Api/
    ├── Endpoints/
    │   └── TodoEndpoints.cs
    └── Program.cs
""", "target-structure.txt", lang="text")}

<h3>Step 1 — Extract the domain entity</h3>
{C(r"""
// BEFORE (in Program.cs or a single Models.cs):
public class TodoItem
{{
    public int Id {{ get; set; }}
    public string Title {{ get; set; }} = "";
    public bool IsComplete {{ get; set; }}
    public DateTime CreatedAt {{ get; set; }}
    public int UserId {{ get; set; }}
}}

// AFTER: TodoApi.Domain/Entities/TodoItem.cs
namespace TodoApi.Domain.Entities;

public sealed class TodoItem
{{
    public int Id {{ get; private set; }}
    public string Title {{ get; private set; }}
    public bool IsComplete {{ get; private set; }}
    public DateTimeOffset CreatedAt {{ get; private set; }}
    public int UserId {{ get; private set; }}

    private TodoItem() {{ Title = ""; }}   // EF parameterless ctor

    public static TodoItem Create(string title, int userId)
    {{
        ArgumentException.ThrowIfNullOrWhiteSpace(title);
        return new TodoItem
        {{
            Title     = title.Trim(),
            IsComplete = false,
            CreatedAt = DateTimeOffset.UtcNow,
            UserId    = userId
        }};
    }}

    public void Complete() => IsComplete = true;
    public void Rename(string newTitle)
    {{
        ArgumentException.ThrowIfNullOrWhiteSpace(newTitle);
        Title = newTitle.Trim();
    }}
}}
""", "TodoItem.cs")}

<h3>Step 2 — Extract the repository interface</h3>
{C(r"""
// TodoApi.Domain/Interfaces/ITodoRepository.cs
namespace TodoApi.Domain.Interfaces;

public interface ITodoRepository
{{
    Task<IReadOnlyList<TodoItem>> GetByUserAsync(int userId, CancellationToken ct);
    Task<TodoItem?> GetByIdAsync(int id, CancellationToken ct);
    Task AddAsync(TodoItem item, CancellationToken ct);
    Task SaveChangesAsync(CancellationToken ct);
    Task DeleteAsync(TodoItem item, CancellationToken ct);
}}
""", "ITodoRepository.cs")}

<h3>Step 3 — Implement in Infrastructure</h3>
{C(r"""
// TodoApi.Infrastructure/Persistence/TodoRepository.cs
namespace TodoApi.Infrastructure.Persistence;

public sealed class TodoRepository(AppDbContext db) : ITodoRepository
{{
    public Task<IReadOnlyList<TodoItem>> GetByUserAsync(int userId, CancellationToken ct)
        => db.Todos
             .Where(t => t.UserId == userId)
             .OrderByDescending(t => t.CreatedAt)
             .AsNoTracking()
             .ToListAsync<TodoItem>(ct)
             .ContinueWith(t => (IReadOnlyList<TodoItem>)t.Result, ct);

    public Task<TodoItem?> GetByIdAsync(int id, CancellationToken ct)
        => db.Todos.FirstOrDefaultAsync(t => t.Id == id, ct);

    public async Task AddAsync(TodoItem item, CancellationToken ct)
        => await db.Todos.AddAsync(item, ct);

    public Task SaveChangesAsync(CancellationToken ct)
        => db.SaveChangesAsync(ct);

    public async Task DeleteAsync(TodoItem item, CancellationToken ct)
    {{
        db.Todos.Remove(item);
        await db.SaveChangesAsync(ct);
    }}
}}
""", "TodoRepository.cs")}

<h3>Step 4 — Application service with DTOs</h3>
{C(r"""
// TodoApi.Application/DTOs/TodoItemDto.cs
public record TodoItemDto(int Id, string Title, bool IsComplete, DateTimeOffset CreatedAt);

// TodoApi.Application/Services/TodoService.cs
public sealed class TodoService(ITodoRepository repo) : ITodoService
{{
    public async Task<IReadOnlyList<TodoItemDto>> GetMyItemsAsync(int userId, CancellationToken ct)
    {{
        var items = await repo.GetByUserAsync(userId, ct);
        return items.Select(i => new TodoItemDto(i.Id, i.Title, i.IsComplete, i.CreatedAt)).ToList();
    }}

    public async Task<TodoItemDto> CreateAsync(string title, int userId, CancellationToken ct)
    {{
        var item = TodoItem.Create(title, userId);
        await repo.AddAsync(item, ct);
        await repo.SaveChangesAsync(ct);
        return new TodoItemDto(item.Id, item.Title, item.IsComplete, item.CreatedAt);
    }}

    public async Task CompleteAsync(int id, int userId, CancellationToken ct)
    {{
        var item = await repo.GetByIdAsync(id, ct)
            ?? throw new NotFoundException($"Todo {{id}} not found");
        if (item.UserId != userId) throw new ForbiddenException();
        item.Complete();
        await repo.SaveChangesAsync(ct);
    }}

    public async Task DeleteAsync(int id, int userId, CancellationToken ct)
    {{
        var item = await repo.GetByIdAsync(id, ct)
            ?? throw new NotFoundException($"Todo {{id}} not found");
        if (item.UserId != userId) throw new ForbiddenException();
        await repo.DeleteAsync(item, ct);
    }}
}}
""", "TodoService.cs")}

<h3>Step 5 — Endpoints stay identical</h3>
{C(r"""
// BEFORE (all in Program.cs, inline EF):
app.MapGet("/api/todos", async (AppDbContext db, ClaimsPrincipal user) =>
    await db.Todos.Where(t => t.UserId == GetUserId(user)).ToListAsync());

// AFTER (Endpoints/TodoEndpoints.cs — same HTTP contract, different internals):
public static class TodoEndpoints
{{
    public static IEndpointRouteBuilder MapTodoEndpoints(this IEndpointRouteBuilder app)
    {{
        var group = app.MapGroup("/api/todos").RequireAuthorization();

        group.MapGet("",    GetAll);
        group.MapPost("",   Create);
        group.MapPatch("{{id}}/complete", Complete);
        group.MapDelete("{{id}}", Delete);

        return app;
    }}

    private static async Task<IResult> GetAll(ITodoService svc, ClaimsPrincipal user, CancellationToken ct)
    {{
        var items = await svc.GetMyItemsAsync(GetUserId(user), ct);
        return Results.Ok(items);
    }}

    private static async Task<IResult> Create(
        CreateTodoRequest req, ITodoService svc, ClaimsPrincipal user, CancellationToken ct)
    {{
        var item = await svc.CreateAsync(req.Title, GetUserId(user), ct);
        return Results.Created($"/api/todos/{{item.Id}}", item);
    }}

    private static async Task<IResult> Complete(
        int id, ITodoService svc, ClaimsPrincipal user, CancellationToken ct)
    {{
        await svc.CompleteAsync(id, GetUserId(user), ct);
        return Results.NoContent();
    }}

    private static async Task<IResult> Delete(
        int id, ITodoService svc, ClaimsPrincipal user, CancellationToken ct)
    {{
        await svc.DeleteAsync(id, GetUserId(user), ct);
        return Results.NoContent();
    }}

    private static int GetUserId(ClaimsPrincipal user)
        => int.Parse(user.FindFirstValue(ClaimTypes.NameIdentifier)!);
}}
""", "TodoEndpoints.cs")}

<h3>Diff summary</h3>
{table(["Area","Before","After"],[
["Code location","All in Program.cs (~250 lines)","4 projects, files averaged 40 lines"],
["Entity","Public setters, no behaviour","Private setters, factory + behaviour methods"],
["Data access","Inline <code>db.Todos.Where(...)</code> in endpoints","<code>ITodoRepository</code> + <code>TodoRepository</code>"],
["Business logic","Inline in MapGet/MapPost lambdas","<code>ITodoService</code> + <code>TodoService</code>"],
["DTOs","EF entity returned directly","<code>TodoItemDto</code> record, no EF navigation properties"],
["HTTP contract","Unchanged","Unchanged (zero breaking changes)"]])}
{tip("Refactor in commits: (1) add projects, move entity; (2) add interface + implementation; (3) move service; (4) rewire Program.cs. Each commit should build and all Postman tests should still pass.")}
''',
["Moving everything in one huge commit — if it breaks, you can't bisect.",
"Changing the endpoint URLs or the JSON field names during the refactor — that breaks clients.",
"Putting business logic (authorization checks like 'does this todo belong to this user') in the endpoint instead of the service.",
"Injecting AppDbContext directly into the service layer — the service layer should depend only on the interface.",
"Forgetting to register the new services in Program.cs — a startup exception is easy to miss."],
("40 min", [
    "Score the To-do, Catalog and Blog APIs with the decision framework above. Record the scores.",
    "On the lowest-scoring project: add the domain project and extract the entity with private setters and at least one behaviour method.",
    "Add the repository interface and move the EF implementation into an Infrastructure project. Register with <code>builder.Services.AddScoped&lt;ITodoRepository, TodoRepository&gt;()</code>."]),
[("What is the dependency inversion principle in this context?","The domain and application layers define interfaces; the infrastructure layer implements them. The API project references the application layer, not the infrastructure layer directly."),
("Why are private setters on a domain entity important?","They enforce that state changes go through methods (Complete(), Rename()) where you can add validation and business rules. Direct property assignment bypasses those rules."),
("Why should DTOs never contain EF navigation properties?","Navigation properties cause lazy or accidental loading, circular reference issues during JSON serialisation (StackOverflowException), and leak persistence concerns into the API contract.")],
[("Basic","What are the layers in a clean ASP.NET Core solution?","Domain (entities, interfaces, value objects, no dependencies). Application (services, use-cases, DTOs; depends on Domain). Infrastructure (EF Core, email, external APIs; depends on Application interfaces). API/Presentation (endpoints, middleware; depends on Application, injects Infrastructure via DI)."),
("Basic","What is a DTO and why use one?","Data Transfer Object: a serialisable record/class returned by or sent to the API, with only the fields clients need. It decouples the API contract from the EF entity, prevents over-posting and over-fetching, and avoids JSON serialiser issues with navigation properties."),
("Intermediate","How do you avoid breaking the API contract during a refactor?","Keep endpoint URLs, HTTP methods and JSON field names identical. Run the full Postman collection after each commit. If you must rename a JSON field, add a JsonPropertyName attribute to map the old name."),
("Intermediate","Where should user-ownership checks (does this todo belong to this user) live?","In the application service, not in the endpoint. The service has the business rule; the endpoint only extracts the userId from the claim and calls the service. This keeps the rule testable without an HTTP context."),
("Intermediate","What is an anemic domain model and why is it considered a problem?","An entity with only public properties and no behaviour — all logic lives in service classes. The problem is that the entity cannot enforce its own invariants; any code can set any property to any invalid state. The fix is to add behaviour methods and use private setters.")])

# ================= DAY 6  SAT =================
d6 = day(6, "SAT", "README polish, Swagger screenshots and CV/LinkedIn bullets",
"Make every Phase 2 project presentable: a standard README, working Swagger, docker-compose, and bullets that read well on an Indian developer's CV and GitHub profile.",
[("README","A project's first impression: explains what it does, how to run it, what endpoints exist — in under 2 minutes of reading."),
("Swagger / OpenAPI","Auto-generated interactive API documentation served at <code>/swagger</code>; generated by Swashbuckle in .NET."),
("docker-compose","A YAML file that starts the API and SQL Server together with one command: <code>docker compose up</code>."),
("Multi-stage build","A Dockerfile with separate build and runtime stages; the runtime image has no SDK, keeping it small."),
("ASCII architecture","A text diagram in the README describing the layers (API → Application → Infrastructure → SQL Server) that renders in any terminal or GitHub markdown."),
("GitHub profile README","A special repo (<code>username/username</code>) whose README appears on your GitHub profile landing page."),
("LinkedIn Summary section","Two to three lines describing your skills and what you are building, written for a recruiter who spends 10 seconds scanning."),
("Quantified bullet","A CV bullet that includes a number: 'Reduced p99 latency from 620 ms to 48 ms by adding a covering index' is stronger than 'improved performance'.")],
["Add a badge to every README: build status, .NET version, licence.",
"Record a 60-second Loom or GIF showing Swagger for the Blog API and embed the link in the README.",
"On LinkedIn, the Projects section is under-used by Indian developers — add every Phase 2 project there with a GitHub link.",
"Keep docker-compose in source control so a new team member can run the full stack with one command.",
"Quantify everything on the CV: row counts, latency improvements, endpoint counts."],
f'''
<h3>1. API README template</h3>
{C(r"""
# Blog API

> ASP.NET Core 8 minimal-API with JWT auth, EF Core 8 and SQL Server 2022.

[![.NET](https://img.shields.io/badge/.NET-8-512BD4)](https://dotnet.microsoft.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What it does
A multi-user blogging API with posts, comments and tag filtering.
Authenticated users may create, edit and delete their own content.
Admins may moderate any content.

## Architecture

```
        HTTP requests
              |
     [Blog.Api  — Minimal API endpoints]
              |
     [Blog.Application  — BlogService, AuthService, DTOs]
              |
     [Blog.Domain  — Post, Comment, Tag entities + interfaces]
              |
     [Blog.Infrastructure  — EF Core, AppDbContext, Repositories]
              |
         SQL Server 2022
```

## Quick start
```bash
git clone https://github.com/nayak22/blog-api.git
cd blog-api
docker compose up          # starts SQL Server + API
# API: http://localhost:5000
# Swagger: http://localhost:5000/swagger
```

## Endpoints summary
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST   | /api/auth/register | — | Create account |
| POST   | /api/auth/login    | — | Returns JWT |
| GET    | /api/posts         | — | Paged list |
| POST   | /api/posts         | ✓ | Create post |
| PUT    | /api/posts/{{id}}    | ✓ owner | Update post |
| DELETE | /api/posts/{{id}}    | ✓ owner | Delete post |
| POST   | /api/posts/{{id}}/comments | ✓ | Add comment |

## Running locally without Docker
```bash
dotnet user-secrets set "ConnectionStrings:Default" "Server=.;Database=BlogDb;Integrated Security=true"
dotnet ef database update --project Blog.Infrastructure
dotnet run --project Blog.Api
```

## Running tests
```bash
dotnet test                       # unit tests
newman run tests/postman/blog-api.json -e tests/postman/local.env.json
```
""", "README.md", lang="text")}

<h3>2. ASCII architecture diagram (copy into README)</h3>
{C(r"""
// For the Product Catalog API (Week 18):

                    ┌─────────────────────────────────────────┐
                    │  Catalog.Api                            │
                    │  Minimal API  ·  Swagger  ·  Rate limit │
                    └───────────────┬─────────────────────────┘
                                    │ DI (interfaces)
                    ┌───────────────▼─────────────────────────┐
                    │  Catalog.Application                    │
                    │  ProductService  ·  DTOs  ·  Validation │
                    └───────────────┬─────────────────────────┘
                                    │
            ┌───────────────────────┴──────────────────────────┐
            │                                                  │
┌───────────▼────────┐                              ┌──────────▼────────┐
│  Catalog.Domain    │                              │  Catalog.Infra    │
│  Product entity    │◄─────── implements ──────────│  EF Core repos    │
│  IProductRepo      │                              │  AppDbContext     │
└────────────────────┘                              └──────────┬────────┘
                                                               │
                                                    ┌──────────▼────────┐
                                                    │  SQL Server 2022  │
                                                    └───────────────────┘
""", "ascii-arch.txt", lang="text")}

<h3>3. docker-compose.yml for API + SQL Server</h3>
{C(r"""
# docker-compose.yml (place at solution root)
version: "3.9"

services:

  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      SA_PASSWORD: "DevPassword@123"      # change for production; use secrets
      ACCEPT_EULA: "Y"
    ports:
      - "1433:1433"
    volumes:
      - sqldata:/var/opt/mssql
    healthcheck:
      test: ["CMD", "/opt/mssql-tools/bin/sqlcmd", "-S", "localhost",
             "-U", "sa", "-P", "DevPassword@123", "-Q", "SELECT 1"]
      interval: 10s
      retries: 5
      start_period: 30s

  api:
    build:
      context: .
      dockerfile: Blog.Api/Dockerfile
    ports:
      - "5000:8080"
    environment:
      ConnectionStrings__Default: "Server=sqlserver;Database=BlogDb;User=sa;Password=DevPassword@123;TrustServerCertificate=True"
      Jwt__Key: "DevSecretKey-change-in-production-32chars!"
      ASPNETCORE_ENVIRONMENT: Development
    depends_on:
      sqlserver:
        condition: service_healthy

volumes:
  sqldata:
""", "docker-compose.yml", lang="yaml")}

<h3>4. Multi-stage Dockerfile</h3>
{C(r"""
# Blog.Api/Dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet restore Blog.Api/Blog.Api.csproj
RUN dotnet publish Blog.Api/Blog.Api.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .

# Apply EF migrations at startup
ENTRYPOINT ["dotnet", "Blog.Api.dll"]
""", "Dockerfile")}

<h3>5. Applying migrations in startup (for containers)</h3>
{C(r"""
// Program.cs — apply pending migrations when the API starts
// Use only in development / staging; in production use a separate migration job
using (var scope = app.Services.CreateScope())
{{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.Migrate();      // safe: no-op if already up to date
}}
""", "Program.cs (migration snippet)")}

<h3>6. GitHub profile README bullets</h3>
{C(r"""
# Hi, I'm Samrath 👋

**Software Engineer @ Light & Wonder** · Building AI-powered tooling and .NET backends

## 🛠 Currently building
- **74-week .NET Full-Stack Roadmap** — Week 22 of 74
  APIs, SQL Server, EF Core, React, Azure (repo: github.com/nayak22/dotnet-roadmap)
- **Ugaav Labs** — agri AI/ML platform for Indian farmers (Python + .NET microservices)

## ⚡ Phase 2 Projects (ASP.NET Core · SQL Server 2022 · EF Core 8)
| Project | Stack | Highlights |
|---------|-------|------------|
| [To-do API](link) | Minimal APIs · JWT · EF Core | Auth, paging, health checks |
| [Product Catalog API](link) | Layered architecture · SQL Server | Covering indexes, rate limiting |
| [Blog API](link) | RBAC · Postman collection | 15 endpoints, Newman in CI |
| [Auth Service](link) | JWT · Refresh tokens · RBAC | Role-based policies |

## 📫 Connect
[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue)](https://linkedin.com/in/samrath)
""", "github-profile-README.md", lang="text")}

<h3>7. CV and LinkedIn bullets for Phase 2 projects</h3>
{C(r"""
// Blog API (Week 19)
// Weak: "Developed a Blog API with JWT authentication"
// Strong:
"Designed and deployed a multi-user Blog REST API (ASP.NET Core 8, EF Core 8, SQL Server 2022) with 15 endpoints, JWT + refresh-token auth, role-based access control (admin/user), paging, and a full Postman/Newman regression suite integrated into GitHub Actions CI."

// Product Catalog API (Week 18)
// Weak: "Built a product catalog with filtering and paging"
// Strong:
"Built a layered Product Catalog API serving 50 000-row datasets; diagnosed and fixed a cartesian N+1 Include query and a leading-wildcard search, reducing SQL logical reads by 69× and p99 latency from 620 ms to 8 ms by applying a covering index."

// Auth Service (Week 20)
// Weak: "Implemented authentication"
// Strong:
"Implemented a standalone JWT authentication service (access token 15 min + HttpOnly refresh cookie) with BCrypt password hashing, RBAC via claims, and a token-revocation blacklist in an in-memory store."
""", lang="text")}
''',
iqs=[("Basic","What is Swagger / OpenAPI?","Swagger is an interactive UI for exploring and testing API endpoints, generated from the OpenAPI specification. In .NET, Swashbuckle scans controllers/endpoints at startup and serves the spec at <code>/swagger/v1/swagger.json</code>. Swagger UI at <code>/swagger</code> renders it. Disable in production or secure it behind auth."),
("Basic","What does docker-compose up do?","It reads docker-compose.yml, pulls or builds images, creates a shared Docker network, starts all services in dependency order, and streams their logs. <code>docker compose down</code> stops and removes the containers; volumes persist unless you add <code>-v</code>."),
("Intermediate","Why use a multi-stage Dockerfile?","The build stage contains the .NET SDK (~700 MB). The runtime stage has only the ASP.NET runtime (~220 MB). The final image is leaner, has a smaller attack surface and deploys faster. The <code>COPY --from=build</code> line picks only the published output."),
("Intermediate","How do you apply EF Core migrations in a Docker container?","Either call <code>db.Database.Migrate()</code> at startup (simple, suits dev/staging), or run a separate <code>dotnet ef database update</code> job before the API starts (safer for production, avoids race conditions when multiple API instances start simultaneously).")])

# ================= DAY 7  SUN =================
d7 = day(7, "SUN", "Phase 2 recap, self-assessment and Phase 3 preview",
"Consolidate 12 weeks of ASP.NET Core + SQL Server + EF Core, score yourself honestly, and get oriented for Phase 3 (front-end: HTML/CSS/JS/React).",
[("Phase 2 (Weeks 11–22)","SQL Server 2022, T-SQL, EF Core 8, ASP.NET Core 8 minimal APIs, JWT auth, SignalR, SSRS-style email reports."),
("Phase 3 (Weeks 23–32)","HTML5, CSS3, Tailwind, JavaScript ES2022, TypeScript, React 18, React Router, TanStack Query, a full-stack project."),
("Self-assessment","Honestly rating your confidence and production-readiness across all Phase 2 topics — not how much you studied, but whether you could ship it tomorrow."),
("Spaced repetition","Come back to amber/red topics in Weeks 23 and 24 before they go stale."),
("Node.js LTS","Required for Phase 3 tooling (npm, Vite, TypeScript compiler, ESLint). Install v22 LTS.")],
["Phase 2 is the foundation. Phase 3 builds the front-end on top. Everything in Phase 3 ultimately talks to the APIs you built.",
"Before starting Phase 3, deploy at least one Phase 2 API cheaply (see the deployment suggestion below) so it's reachable from the internet.",
"The Phase 3 setup takes about 30 minutes; do it today so Day 1 of Week 23 goes straight into code.",
"Your GitHub profile and CV bullets are your portfolio until you have a full-stack project to show.",
"Phase 3 Week 23 is HTML and CSS — deceptively important for interviews at Indian product companies (Flipkart, Meesho, Razorpay front-end rounds)."],
f'''
<h3>Phase 2 self-assessment table (Weeks 11–22)</h3>
<p>Rate each topic 1–5: 1 = never tried, 3 = works in my project, 5 = could explain in an interview and fix production issues.</p>
{table(["Week","Topic","Rate 1–5","Notes / next action"],[
["W11","SQL Server setup, T-SQL basics (DDL, DML, WHERE, JOIN)","",""],
["W12","Aggregates, subqueries, CTEs, window functions","",""],
["W13","Stored procedures, indexes, execution plans","",""],
["W14","EF Core setup, DbContext, migrations, CRUD","",""],
["W15","LINQ in depth, AsNoTracking, projections","",""],
["W16","Relationships (one-to-many, many-to-many), owned types","",""],
["W17","ASP.NET Core minimal APIs, routing, DI","",""],
["W18","Layered architecture, DTOs, paging, Repository","",""],
["W19","JWT auth integration, [Authorize], RBAC","",""],
["W20","Auth service, refresh tokens, identity","",""],
["W21","SignalR real-time, background services, email reports","",""],
["W22","Production checklist, Postman/Newman, slow-query fix, refactoring","",""]])}
<p class="muted">Print or copy this table into your dotnet-notes repo. Revisit amber (3) and red (1–2) rows in Week 23 and 24 buffer slots.</p>

<h3>Deploy one API cheaply (optional but recommended)</h3>
{C(r"""
# Option 1: Railway.app (free tier, SQL Server not available — use PostgreSQL with Npgsql)
# Full deployment is in Phase 4 (Week 42+). Today: just understand the options.

# Option 2: Azure App Service (Free F1 tier) + Azure SQL (serverless free tier)
# az webapp create --resource-group rg-blog --plan free-plan --name blog-api-samrath
# az sql server create ... (requires credit card for identity verification, billed on pause)

# Option 3: Render.com + PlanetScale (MySQL) — no SQL Server
# Not ideal for Phase 2 code but quick to get a URL

# Cheapest path that keeps SQL Server:
# Azure App Service (Free) + Azure SQL Database (5 DTU Basic ~₹500/month)
# or: a ₹200/month VPS (DigitalOcean, Hetzner, Vultr) with SQL Server Express (free) + Docker
""", lang="bash")}
{tip("Full deployment to Azure App Service + SQL Server with CI/CD is covered in Phase 4 (Week 42). For now, just getting a URL you can share is enough — it makes your GitHub projects look live.")}

<h3>Phase 3 setup (Node LTS + VS Code extensions)</h3>
{C(r"""
# 1. Install Node.js v22 LTS (current LTS as of 2026)
# Download from nodejs.org or use nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
nvm install 22
nvm use 22
node --version    # v22.x.x

# 2. VS Code extensions for Phase 3
# ES7+ React/Redux/React-Native snippets  (dsznajder.es7-react-js-snippets)
# Prettier — Code formatter               (esbenp.prettier-vscode)
# ESLint                                  (dbaeumer.vscode-eslint)
# Tailwind CSS IntelliSense               (bradlc.vscode-tailwindcss)
# TypeScript Hero (auto imports)          (rbbit.typescript-hero)
# CSS Peek                                (pranaygp.vscode-css-peek)

# Install all via CLI:
code --install-extension esbenp.prettier-vscode
code --install-extension dbaeumer.vscode-eslint
code --install-extension bradlc.vscode-tailwindcss

# 3. Quick smoke test — Vite React scaffold (you'll use this in Week 25)
npm create vite@latest hello-react -- --template react-ts
cd hello-react
npm install
npm run dev    # opens at http://localhost:5173
""", "phase3-setup.sh", lang="bash")}

<h3>Phase 3 preview — Weeks 23–32</h3>
{table(["Week","Topic","Project"],[
["W23","HTML5 semantics, CSS3, Flexbox, Grid","Personal landing page"],
["W24","JavaScript ES2022: modules, async/await, fetch","Blog UI (plain JS)"],
["W25","TypeScript: types, interfaces, generics, strict","Typed utilities"],
["W26","React 18: JSX, state, props, effects","To-do UI"],
["W27","React Router, nested layouts, protected routes","Multi-page app"],
["W28","Forms, validation, controlled/uncontrolled components","Blog editor"],
["W29","TanStack Query: data fetching, caching, mutations","Catalog browser"],
["W30","Tailwind CSS + design system","Polish all UIs"],
["W31","Full-stack: React front-end calling Blog API","Blog full-stack"],
["W32","Phase 3 exit check","Portfolio site"]])}

<h3>Phase 2 — final revision checklist</h3>
<ul>
<li>Can you explain a SQL execution plan to a colleague?</li>
<li>Can you add a migration with EF Core and roll it back?</li>
<li>Can you write a minimal API endpoint with validation, auth, paging and health checks?</li>
<li>Can you trace a JWT from login to a protected endpoint?</li>
<li>Can you identify and fix an N+1 query?</li>
<li>Can you run the Postman collection with Newman?</li>
<li>Are all five Phase 2 projects on GitHub with a README and docker-compose?</li>
</ul>

<h3>5-question quiz — predict the output or spot the bug</h3>
<details><summary>Q1. What HTTP status should POST /api/orders return when the order is created?</summary>
<b>201 Created</b>, with a <code>Location: /api/orders/42</code> header. <code>200 OK</code> is wrong for resource creation.
</details>
<details><summary>Q2. The Blog API returns 500 on every request. EF Core logs show the error. What is the most likely cause in a Docker Compose setup?</summary>
{C(r"""
// API starts before SQL Server is ready, so the first migration call fails.
// Fix 1: add a healthcheck on the sqlserver service and depends_on condition: service_healthy.
// Fix 2: wrap db.Database.Migrate() in a retry policy (Polly).
"Server=sqlserver;Database=BlogDb;Connect Timeout=30"  // also increase connect timeout
""")}<b>Race condition:</b> the API container starts before SQL Server is ready. Add <code>depends_on: condition: service_healthy</code> in docker-compose.yml.
</details>
<details><summary>Q3. Does this compile and what does it return?</summary>
{C(r"""
app.MapGet("/api/posts", async (AppDbContext db) =>
    await db.Posts
        .Include(p => p.Comments)
        .Select(p => new {{ p.Id, p.Title, CommentCount = p.Comments.Count }})
        .ToListAsync());
""")}<b>Yes, it compiles and returns.</b> EF Core translates this to SQL: <code>SELECT p.Id, p.Title, COUNT(c.Id) AS CommentCount FROM Posts p LEFT JOIN Comments c ON c.PostId = p.Id GROUP BY p.Id, p.Title</code>. You cannot use <code>Include</code> and <code>Select</code> together on the same navigation in older EF versions — but in EF Core 8, the <code>Include</code> is ignored when a projection (<code>Select</code>) is used; the projection drives the SQL.</details>
<details><summary>Q4. A developer adds a Scoped service to a Singleton. What happens in Development?</summary>
<b>InvalidOperationException at startup</b>: "Cannot consume scoped service 'XyzService' from singleton 'AbcService'." ASP.NET Core's scope validation checks this at app startup in Development. In Production (without ValidateScopes), it silently creates a captive dependency.
</details>
<details><summary>Q5. Rate the fix: change <code>LIKE '%' + @search + '%'</code> to <code>LIKE @search + '%'</code>. Is it complete?</summary>
<b>Partially correct.</b> Removing the leading <code>%</code> makes the pattern index-sargable (SQL Server can seek). But you must also ensure an index on the searched column; without it, the query still scans. Add <code>HasIndex(p => p.Name)</code> in entity configuration and run a migration.
</details>

{iq([("Basic","What does <code>db.Database.Migrate()</code> do?","It applies all pending EF Core migrations to the database in order, creating tables and altering schema as needed. It is safe to call on a database that is already up to date — it checks the __EFMigrationsHistory table and does nothing."),
("Basic","What is the difference between authentication and authorization?","Authentication establishes who you are (validate the JWT, extract claims). Authorization decides what you are allowed to do (check roles/policies on the endpoint). In ASP.NET Core, <code>UseAuthentication</code> must come before <code>UseAuthorization</code> in the pipeline."),
("Intermediate","How does the Blog API know which user made the request?","The JWT middleware validates the token's signature and expiry, then sets <code>HttpContext.User</code> as a <code>ClaimsPrincipal</code>. The endpoint reads <code>user.FindFirstValue(ClaimTypes.NameIdentifier)</code> to get the userId from the <code>sub</code> claim."),
("Intermediate","What is the best way to handle a 'not found' result in a minimal API?","Return <code>Results.NotFound()</code> (404) rather than null or 200. For consistency, use a global exception handler: throw a <code>NotFoundException</code> in the service layer; the handler converts it to 404 ProblemDetails automatically.")])}

<div class="note tip"><b>Next week:</b> Phase 3 begins — Week 23: HTML5 semantics, CSS3, Flexbox and Grid. You will build a personal landing page and learn how browsers render a document. Set up Node.js and the VS Code extensions listed above before Week 23 Day 1.</div>
''')

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
    (1,"MON","Production checklist for APIs","Prod checklist","Status codes, ProblemDetails, auth on mutations, no PII in logs, health checks, rate limits, paging caps, CancellationToken, migrations.","2 hrs"),
    (2,"TUE","Postman collection for the Blog API","Postman/Newman","Environments, variables, login script storing token, pre-request Bearer, pm.test checks, Newman CI.","2 hrs"),
    (3,"WED","Fix one slow query end to end","Slow-query runbook","Capture, diagnose, fix leading wildcard + missing index + cartesian Include; verify logical reads.","2 hrs"),
    (4,"THU","Explain aloud — interview prep","Explain aloud","Model answers for DI lifetimes, middleware order, JWT, clustered vs non-clustered, change tracking, N+1.","2 hrs"),
    (5,"FRI","Refactor the weakest repo","Refactor","Decision framework; move To-do API into 4-project layered shape without breaking endpoints.","2 hrs"),
    (6,"SAT","README polish and CV/LinkedIn bullets","README &amp; CV","API README template, ASCII arch, docker-compose, GitHub profile, quantified CV bullets.","4 hrs"),
    (7,"SUN","Phase 2 recap and Phase 3 preview","Phase 2 exit","Self-assessment table W11–22, 5-question quiz, Phase 3 setup, deploy suggestion, next week preview.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week22.html", 22,
      "Week 22 — Phase 2 Exit Check",
      "Phase 2", "~18 hrs",
      ["Phase 2 · Week 22 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "Phase 2 exit"],
      "Week 22 is the Phase 2 exit check. You will audit every API project from Weeks 17–21 against a production checklist, build a complete Postman/Newman test suite, diagnose and fix a slow SQL query end to end, practise verbal answers for the six most common interview topics, refactor the weakest project into a clean layered structure, polish every project README with docker-compose and CV-ready bullets, and score yourself honestly before Phase 3 begins next week.",
      cards, days)
print("built")
