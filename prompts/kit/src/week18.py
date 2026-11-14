import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1  MON =================
d1 = day(1, "MON", "REST Principles and HTTP Semantics",
"Understand URIs, verbs, idempotency, status codes, and RFC 9457 ProblemDetails so every endpoint you build speaks fluent HTTP.",
[("REST","Representational State Transfer — an architectural style using resources, URIs, uniform verbs, stateless requests and self-descriptive messages."),
("Resource","A noun in your API — a Product, Order or Category — identified by a URI."),
("URI","Uniform Resource Identifier: the stable address of a resource, e.g. <code>/api/v1/products/42</code>."),
("Safe method","An HTTP method that does not modify server state: GET and HEAD."),
("Idempotent method","Calling it once or N times leaves the server in the same state: GET, PUT, DELETE, HEAD, OPTIONS."),
("POST","Creates a subordinate resource or triggers a command; neither safe nor idempotent."),
("PUT","Replaces a resource completely; idempotent."),
("PATCH","Partial update; not guaranteed idempotent — depends on the semantics."),
("204 No Content","Success with no response body — common for PUT, PATCH, DELETE."),
("201 Created","Resource was created; <em>must</em> include a <code>Location</code> header with the new resource URI."),
("409 Conflict","Request conflicts with current state: duplicate slug, optimistic-concurrency clash."),
("422 Unprocessable Content","Well-formed request that fails business/validation rules — the right code for validation errors."),
("ProblemDetails","RFC 9457 JSON structure for error responses: <code>type</code>, <code>title</code>, <code>status</code>, <code>detail</code>, <code>instance</code>."),
("HATEOAS","Hypermedia As The Engine Of Application State — responses include links to related actions; awareness is enough for most real-world APIs.")],
["Use nouns for resource URIs, not verbs: <code>/products</code> not <code>/getProducts</code>.",
"Always return 201 + Location for POST creates so callers know where the new resource lives.",
"Use 422 (not 400) when input is structurally valid JSON but fails business validation.",
"ProblemDetails with <code>errors</code> extension lets FluentValidation field errors flow cleanly.",
"Keep URIs lowercase and hyphenated: <code>/product-categories</code>, not <code>/ProductCategories</code>.",
"Stateless means no session on the server — every request carries all it needs (auth token, etc.)."],
f'''
<h3>1. Verbs, safety, idempotency</h3>
{table(["Verb","Safe","Idempotent","Typical use","Success code"],[
["GET","Yes","Yes","Fetch resource or collection","200"],
["HEAD","Yes","Yes","Like GET, headers only","200"],
["OPTIONS","Yes","Yes","CORS preflight, discover allowed methods","200/204"],
["POST","No","No","Create a subordinate resource or trigger a command","201 / 200 / 202"],
["PUT","No","Yes","Full replace of a resource","200 / 204"],
["PATCH","No","No*","Partial update","200 / 204"],
["DELETE","No","Yes","Remove a resource","204 / 200"]])}
<p class="muted">* PATCH is idempotent if the patch is absolute (set price=499), not if it's relative (increment price by 50).</p>

<h3>2. Status codes to know cold</h3>
{table(["Code","Meaning","When to use"],[
["200 OK","Success with body","GET, PUT/PATCH that returns the updated resource"],
["201 Created","New resource; Location header present","POST that creates"],
["204 No Content","Success, no body","DELETE, PUT/PATCH when you return nothing"],
["400 Bad Request","Malformed syntax, missing required field","JSON that won't parse"],
["401 Unauthorized","Missing or invalid credentials","No/bad JWT"],
["403 Forbidden","Authenticated but not allowed","Role check failed"],
["404 Not Found","Resource doesn't exist","Id not in DB"],
["409 Conflict","State clash","Duplicate slug, optimistic-concurrency"],
["422 Unprocessable Content","Validation failure","FluentValidation errors"],
["500 Internal Server Error","Unhandled exception","Never swallow — log and return ProblemDetails"]])}

<h3>3. ProblemDetails — RFC 9457</h3>
<p>ASP.NET Core produces this JSON by default when you throw or return a problem result. Register <code>IExceptionHandler</code> to convert unhandled exceptions into ProblemDetails and avoid leaking stack traces.</p>
{C(r"""
// Program.cs
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

app.UseExceptionHandler();   // must be early in the pipeline
""", "Program.cs (excerpt)")}
{C(r"""
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace Catalog.Api;

public sealed class GlobalExceptionHandler : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _log;

    public GlobalExceptionHandler(ILogger<GlobalExceptionHandler> log) => _log = log;

    public async ValueTask<bool> TryHandleAsync(
        HttpContext ctx, Exception ex, CancellationToken ct)
    {
        _log.LogError(ex, "Unhandled exception");

        var problem = new ProblemDetails
        {
            Type    = "https://tools.ietf.org/html/rfc9110#section-15.6.1",
            Title   = "An unexpected error occurred",
            Status  = StatusCodes.Status500InternalServerError,
            Detail  = ex.Message,       // sanitise in production — don't expose internals
            Instance = ctx.Request.Path
        };
        problem.Extensions["traceId"] = ctx.TraceIdentifier;

        ctx.Response.StatusCode = StatusCodes.Status500InternalServerError;
        await ctx.Response.WriteAsJsonAsync(problem, ct);
        return true;
    }
}
""", "GlobalExceptionHandler.cs")}
{C(r"""
// A validation ProblemDetails payload (422)
// {
//   "type":   "https://tools.ietf.org/html/rfc9110#section-15.5.21",
//   "title":  "One or more validation errors occurred.",
//   "status": 422,
//   "errors": {
//     "Name":  ["'Name' must not be empty."],
//     "Price": ["'Price' must be greater than 0."]
//   }
// }
""", "example-validation-response.json", lang="json")}

<h3>4. 201 Created with Location</h3>
{C(r"""
// Minimal API
app.MapPost("/api/v1/products", async (CreateProductRequest req, IProductService svc) =>
{{
    var product = await svc.CreateAsync(req);
    // Results.Created sets status 201 and the Location header
    return Results.Created($"/api/v1/products/{{product.Id}}", product);
}});

// Controller API
[HttpPost]
public async Task<IActionResult> Create(CreateProductRequest req)
{{
    var product = await _svc.CreateAsync(req);
    return CreatedAtAction(nameof(GetById), new {{ id = product.Id }}, product);
    // → 201 + Location: /api/v1/products/42
}}
""", "ProductsEndpoint.cs (excerpt)")}

<h3>5. HATEOAS — awareness level</h3>
<p>Full HATEOAS embeds links in every response so clients can discover transitions without hardcoded URIs.  Most teams implement a lightweight subset — links to self, next-page, related resources — using plain JSON rather than a full media type like HAL or JSON:API.  Knowing what it is matters for interviews; implementing the full RFC is overkill for most projects.</p>
{C(r"""
// Lightweight "links" extension on a response DTO
public record ProductResponse(int Id, string Name, decimal Price)
{{
    public Dictionary<string, string> Links {{ get; init; }} = [];
}}

// When building the response
var resp = new ProductResponse(p.Id, p.Name, p.Price)
{{
    Links = new Dictionary<string, string>
    {{
        ["self"]     = $"/api/v1/products/{{p.Id}}",
        ["category"] = $"/api/v1/categories/{{p.CategoryId}}"
    }}
}};
""", "ProductResponse.cs (excerpt)")}
''',
["Putting verbs in URIs: <code>/getProduct/1</code> — use GET <code>/products/1</code> instead.",
"Returning 200 with an error body — use the correct 4xx/5xx code.",
"Omitting the <code>Location</code> header on 201 responses.",
"Using 400 for validation failures — 422 is more precise and expected by clients.",
"Leaking exception details in ProblemDetails in production."],
("40 min", [
    "Design URI structure for a product catalog: list, single item, create, update, delete, list by category. Write it as a table.",
    "Add <code>GlobalExceptionHandler</code> to the Week 17 To-Do API and test it throws a 500 ProblemDetails instead of a stack trace.",
    "Return a 201 with <code>Location</code> header from the to-do create endpoint using <code>Results.Created</code>."
]),
[("What does idempotent mean for DELETE?","Sending DELETE /products/42 multiple times returns 204 on the first call and 404 on subsequent calls, but the server state is the same after each — the item is gone."),
("When is 400 the right code versus 422?","400 for requests that can't be parsed (malformed JSON, missing Content-Type). 422 for syntactically valid requests that fail semantic validation rules."),
("What fields does ProblemDetails require?","<code>status</code> (HTTP status code) and <code>title</code> are the minimum. <code>type</code>, <code>detail</code> and <code>instance</code> are strongly recommended.")],
[("Basic","What does REST stand for and what are its key constraints?","Representational State Transfer. Key constraints: client–server, stateless (no server-side session), cacheable, uniform interface (URIs, verbs, ProblemDetails), layered system, code on demand (optional). Stateless and uniform interface are what most people mean day-to-day."),
("Basic","What is the difference between PUT and PATCH?","PUT sends a complete replacement of the resource; the client must supply every field or risk clearing unset fields. PATCH sends only the changed fields. PATCH is not guaranteed idempotent; PUT is."),
("Basic","Why return 422 instead of 400 for validation errors?","400 means the request was malformed at the HTTP/syntax level (can't parse JSON, missing Content-Type). 422 means the request was syntactically correct but semantically invalid — the server understood it, but it failed business rules. RFC 9110 defines them separately."),
("Basic","What must a 201 Created response include?","A <code>Location</code> header pointing to the URI of the newly created resource. Without it, the caller has no way to fetch or reference what was just created."),
("Intermediate","What is IExceptionHandler in ASP.NET Core?","An interface (added in .NET 8) that centralises unhandled-exception handling. Implement <code>TryHandleAsync</code> to convert any thrown exception into a consistent ProblemDetails response. Register with <code>AddExceptionHandler&lt;T&gt;</code> and add <code>app.UseExceptionHandler()</code> to the pipeline."),
("Intermediate","What is HATEOAS and do real APIs implement it?","Hypermedia As The Engine Of Application State: responses include hyperlinks to available next actions so clients don't need out-of-band documentation to navigate. Few real-world REST APIs implement full HATEOAS (HAL, JSON:API). Most implement a lightweight subset — a links dictionary with self, related, and pagination URLs.")])

# ================= DAY 2  TUE =================
d2 = day(2, "TUE", "DTOs, Mapping and Records",
"Separate your API surface from your domain model with request/response DTOs, avoid over-posting and cycles, and choose a mapping strategy that fits your team.",
[("DTO","Data Transfer Object — a plain class or record carrying only the fields needed for one use case, with no behaviour."),
("Over-posting","Client sends extra fields (e.g. <code>IsAdmin=true</code>) that get bound to a model property that shouldn't be settable via the API."),
("Circular reference","Two navigation properties pointing at each other; serialising naively causes infinite recursion."),
("Request DTO","Carries the caller's input for one operation: <code>CreateProductRequest</code>, <code>UpdateProductRequest</code>."),
("Response DTO","Shapes what the caller receives; may include computed fields or omit sensitive data."),
("Manual mapping","Writing a constructor or static factory method that explicitly copies fields — verbose but transparent."),
("Mapster","A source-generated or reflection-based mapping library. Fast; zero config for matching names; NuGet <code>Mapster</code>."),
("AutoMapper","Mature reflection-based mapper. <strong>Caution:</strong> in 2025 AutoMapper moved to a commercial license for large organisations — verify your situation before adopting it on a commercial project."),
("record","An immutable-by-default reference type with value equality; ideal for DTOs because accidental mutation is impossible."),
("init-only setter","A <code>set</code> accessor callable only during object construction or in object-initialisers — not after."),
("Primary constructor","C# 12 syntax: parameters declared on the class/record header, available throughout the class body.")],
["Prefer one DTO per operation (<code>CreateProductRequest</code>, <code>UpdateProductRequest</code>) over one shared DTO.",
"Records for response DTOs; mutable classes (or records with <code>init</code>) for request DTOs that model binders must populate.",
"Map in a service or dedicated mapper class — never in the controller/endpoint.",
"Always whitelist properties a client may set via <code>[Bind]</code> or by using a dedicated request DTO.",
"Mapster can generate source code at build time (zero reflection, AOT-friendly): prefer <code>Mapster.Tool</code> for performance-critical paths.",
"AutoMapper's 2025 commercial licensing change: free for open-source / small teams, but verify your licence tier for commercial use."],
f'''
<h3>1. Why DTOs?</h3>
{C(r"""
// ❌ Exposing the entity directly — over-posting risk
[HttpPost] public async Task<IActionResult> Create(Product product) {{ ... }}

// If the POST body includes "IsActive": true or "StockCount": 999
// those fields get written straight to the entity.

// ✓ Use a request DTO that declares exactly what the client may send
[HttpPost] public async Task<IActionResult> Create(CreateProductRequest req) {{ ... }}
""", "ProductsController.cs (bad vs good)")}
{C(r"""
// Request DTOs — one per operation
public record CreateProductRequest(
    string Name,
    string Slug,
    decimal Price,
    int CategoryId,
    string? Description = null);

public record UpdateProductRequest(
    string Name,
    decimal Price,
    string? Description = null);   // Slug and CategoryId not updatable via this endpoint

// Response DTO — computed fields, hides internal Ids
public record ProductResponse(
    int    Id,
    string Name,
    string Slug,
    decimal Price,
    string CategoryName,
    bool   InStock);
""", "ProductDtos.cs")}

<h3>2. Manual mapping — explicit and debuggable</h3>
{C(r"""
namespace Catalog.Core.Mapping;

public static class ProductMapper
{{
    public static ProductResponse ToResponse(Product p) =>
        new(p.Id, p.Name, p.Slug, p.Price, p.Category.Name, p.StockCount > 0);

    public static Product ToEntity(CreateProductRequest req) =>
        new()
        {{
            Name        = req.Name.Trim(),
            Slug        = req.Slug.ToLowerInvariant().Trim(),
            Price       = req.Price,
            CategoryId  = req.CategoryId,
            Description = req.Description,
            IsActive    = true,
            CreatedAt   = DateTimeOffset.UtcNow
        }};

    public static void ApplyUpdate(Product target, UpdateProductRequest src)
    {{
        target.Name        = src.Name.Trim();
        target.Price       = src.Price;
        target.Description = src.Description;
        target.UpdatedAt   = DateTimeOffset.UtcNow;
    }}
}}
""", "ProductMapper.cs")}

<h3>3. Mapster — fast zero-config mapping</h3>
<p>Mapster maps by convention (matching names), is several times faster than AutoMapper on benchmarks, and can generate source code for AOT-safe builds.  Add <code>Mapster</code> and optionally <code>Mapster.DependencyInjection</code> from NuGet.</p>
{C(r"""
// No configuration needed when property names match
ProductResponse resp = product.Adapt<ProductResponse>();

// When names differ or you need custom logic, configure once at startup
TypeAdapterConfig<Product, ProductResponse>.NewConfig()
    .Map(dest => dest.CategoryName, src => src.Category.Name)
    .Map(dest => dest.InStock,      src => src.StockCount > 0);

// In Program.cs — scan assemblies for TypeAdapterConfig subclasses
var config = TypeAdapterConfig.GlobalSettings;
config.Scan(Assembly.GetExecutingAssembly());
builder.Services.AddSingleton(config);
builder.Services.AddScoped<IMapper, ServiceMapper>();

// Injected mapper (testable)
public class ProductService(IProductRepository repo, IMapper mapper)
{{
    public async Task<ProductResponse> GetByIdAsync(int id)
    {{
        var p = await repo.GetByIdAsync(id)
            ?? throw new NotFoundException($"Product {{id}} not found");
        return mapper.Map<ProductResponse>(p);
    }}
}}
""", "MapsterSetup.cs")}

<h3>4. AutoMapper — caution on licensing</h3>
{C(r"""
// AutoMapper usage looks almost identical to Mapster
// BUT verify your licence: in 2025 AutoMapper changed to a commercial licence
// for companies over a revenue threshold. Check https://automapper.org for terms.
// For greenfield projects consider Mapster or manual mapping instead.

// If you do use AutoMapper, declare a Profile
public class CatalogProfile : Profile
{{
    public CatalogProfile()
    {{
        CreateMap<Product, ProductResponse>()
            .ForMember(d => d.CategoryName, o => o.MapFrom(s => s.Category.Name))
            .ForMember(d => d.InStock,      o => o.MapFrom(s => s.StockCount > 0));

        CreateMap<CreateProductRequest, Product>()
            .ForMember(d => d.Slug, o => o.MapFrom(s => s.Slug.ToLowerInvariant()))
            .ForMember(d => d.IsActive, o => o.UseValue(true));
    }}
}}
""", "CatalogProfile.cs (AutoMapper)")}

<h3>5. Records as DTOs</h3>
{C(r"""
// Positional record — constructor + deconstruct + value equality for free
public record CreateProductRequest(string Name, string Slug, decimal Price, int CategoryId);

// With optional and default values — requires { init; } syntax
public record UpdateProductRequest
{{
    public required string Name  {{ get; init; }}
    public required decimal Price {{ get; init; }}
    public string? Description   {{ get; init; }}
}}

// Response record — read-only after construction, safe to pass around
public record ProductResponse(int Id, string Name, decimal Price, bool InStock);

// Deserialization works with both positional and init-only records in System.Text.Json
// — System.Text.Json can deserialize positional records with matching constructor params
var req = JsonSerializer.Deserialize<CreateProductRequest>(json);
""", "DtoRecords.cs")}
{tip("Use <code>required</code> properties (C# 11+) on request DTOs to get compile-time enforcement even when not using positional records. The model binder and JsonSerializer both respect them.")}
{warn("Avoid putting <code>[JsonIgnore]</code> on entity navigation properties to fix serialisation cycles — use a response DTO instead. The <code>[JsonIgnore]</code> attribute silently drops data in ways callers don't expect.", "Design smell")}
''',
["Sharing one DTO for create, update and response — each operation has different required fields.",
"Mapping inside a controller action — move it to a service or mapper class.",
"Returning the EF entity directly (causes cycle serialisation errors, exposes internal fields).",
"Using AutoMapper without checking your project's licence situation.",
"Mutable records with <code>set</code> instead of <code>init</code> — prefer <code>init</code> for response DTOs."],
("35 min", [
    "Write <code>CreateProductRequest</code>, <code>UpdateProductRequest</code> and <code>ProductResponse</code> records for a kurta product catalog.",
    "Write a static <code>ProductMapper</code> class and unit-test <code>ToResponse</code> with a hand-crafted <code>Product</code> entity.",
    "Add Mapster to a test project; configure a custom mapping for <code>InStock</code> and verify it via <code>TypeAdapterConfig.GlobalSettings.Compile()</code>."
]),
[("Why is a request DTO better than <code>[Bind]</code> attribute for over-posting protection?","A DTO is a whitelist by definition — only fields that exist on it can be populated. <code>[Bind]</code> is a list of exclusions on the entity itself that is easy to forget to update."),
("Why are records preferred for response DTOs?","Immutability (init setters), value equality (useful in tests), concise syntax, and no accidental mutation after the mapping step."),
("What is the difference between Mapster and AutoMapper?","Both map by name convention. Mapster is faster, has source generation support and is free (MIT). AutoMapper is older, has a larger ecosystem, but moved to a commercial licence in 2025 for some usage tiers.")],
[("Basic","What is a DTO and why use one?","A Data Transfer Object carries only the fields needed for a specific operation between layers or over the wire. Using DTOs decouples the API surface from the domain model, prevents over-posting, avoids serialisation issues with EF navigation properties and lets each operation define its own shape."),
("Basic","What is over-posting and how do you prevent it?","Over-posting happens when a client sends extra fields (e.g. <code>IsAdmin=true</code>) that the server model-binds onto sensitive properties. Prevention: use a dedicated request DTO that only declares the fields the client may set. Never bind an EF entity directly."),
("Basic","When would you use <code>init</code> vs <code>set</code> on a DTO property?","<code>init</code> (C# 9+) allows the property to be set only during object construction or in an object initialiser. Use it on response DTOs and value objects to enforce immutability. Use <code>set</code> on request DTOs only if something needs to mutate them post-construction (rare)."),
("Intermediate","How does Mapster source generation work and why does it matter?","With <code>Mapster.Tool</code>, mapping code is generated at build time into plain C# extension methods, so at runtime there is no reflection, no expression compilation and no JIT warmup. It is compatible with AOT (Native AOT / Blazor WASM) and produces code you can read and debug."),
("Intermediate","How do you prevent circular reference errors when serialising EF entities?","Use response DTOs that only copy the flat fields you need — no navigation properties. Alternatively configure <code>JsonSerializerOptions.ReferenceHandler = ReferenceHandler.IgnoreCycles</code> in <code>AddControllers()</code>, but this is a band-aid; the real fix is to never serialise entities directly."),
("Intermediate","AutoMapper vs manual mapping — when is each appropriate?","Manual mapping is best for small projects, teams that value explicitness, or when mappings are complex and bespoke. Mapster suits medium-to-large projects that want convention-based mapping with good performance. AutoMapper is acceptable if you have an existing codebase using it and have confirmed your licence. For new commercial projects in 2025, prefer Mapster or manual mapping.")])

# ================= DAY 3  WED =================
d3 = day(3, "WED", "FluentValidation",
"Write expressive, testable validation rules, wire them into ASP.NET Core's pipeline, and return 422 responses with per-field error details.",
[("FluentValidation","A .NET library that uses a fluent builder API to define validation rules separate from the model class. NuGet: <code>FluentValidation.AspNetCore</code>."),
("AbstractValidator&lt;T&gt;","Base class for a validator; override or chain rules in the constructor with <code>RuleFor</code>."),
("RuleFor","Starts a rule chain for a specific property: <code>RuleFor(x =&gt; x.Name).NotEmpty().MaximumLength(200)</code>."),
("Must / Custom","Escape hatch for logic too complex for built-in rules; <code>Must(val =&gt; ...)</code> or <code>Custom((val, ctx) =&gt; ...)</code>."),
("MustAsync / CustomAsync","Same as above but accepts a cancellation token and returns <code>Task&lt;bool&gt;</code> — use for database uniqueness checks."),
("WithMessage","Overrides the default error message for a rule."),
("Cascade mode","<code>CascadeMode.Stop</code> stops validating a property after the first failure (default for a property in FV11+)."),
("Endpoint filter","A minimal-API hook that runs before the endpoint delegate; used to auto-validate DTOs and short-circuit with 422."),
("Data annotations","<code>[Required]</code>, <code>[MaxLength]</code>, etc. — built into .NET. Simpler but mixed with the model, harder to test, less expressive."),
("ValidationProblemDetails","ASP.NET Core's subtype of ProblemDetails that adds an <code>errors</code> dictionary mapping field names to error arrays.")],
["Register validators with <code>builder.Services.AddValidatorsFromAssemblyContaining&lt;CreateProductRequestValidator&gt;()</code>.",
"Prefer FluentValidation over data annotations for complex rules, async checks and when rules live separately from the DTO.",
"Use data annotations only for truly simple structural constraints (<code>[EmailAddress]</code>, <code>[Range]</code>) if your team prefers them.",
"Always return 422 (not 400) for FluentValidation failures — configure <code>InvalidModelStateResponseFactory</code>.",
"Test validators in isolation: instantiate the validator class and call <code>TestValidateAsync</code>."],
f'''
<h3>1. A validator for Catalog API</h3>
{C(r"""
using FluentValidation;
using Catalog.Core.Dtos;

namespace Catalog.Core.Validators;

public class CreateProductRequestValidator : AbstractValidator<CreateProductRequest>
{{
    public CreateProductRequestValidator(IProductRepository repo)
    {{
        RuleFor(x => x.Name)
            .NotEmpty().WithMessage("Product name is required.")
            .MaximumLength(200).WithMessage("Name must be 200 characters or fewer.");

        RuleFor(x => x.Slug)
            .NotEmpty()
            .Matches(@"^[a-z0-9-]{{3,100}}$")
            .WithMessage("Slug must be 3–100 lowercase alphanumeric characters or hyphens.");

        RuleFor(x => x.Price)
            .GreaterThan(0).WithMessage("Price must be greater than ₹0.")
            .LessThanOrEqualTo(1_000_000m).WithMessage("Price cannot exceed ₹10,00,000.");

        RuleFor(x => x.CategoryId)
            .GreaterThan(0).WithMessage("A valid category is required.")
            .MustAsync(async (id, ct) => await repo.CategoryExistsAsync(id))
            .WithMessage("Category not found.");

        RuleFor(x => x.StockCount)
            .GreaterThanOrEqualTo(0).WithMessage("Stock cannot be negative.");

        // Conditional: description length only matters when provided
        When(x => x.Description is not null, () =>
        {{
            RuleFor(x => x.Description)
                .MaximumLength(2000).WithMessage("Description must be 2 000 characters or fewer.");
        }});
    }}
}}
""", "CreateProductRequestValidator.cs")}

<h3>2. Registering and auto-triggering in minimal APIs</h3>
{C(r"""
// Program.cs
builder.Services.AddValidatorsFromAssemblyContaining<CreateProductRequestValidator>();

// Endpoint filter that validates any T and short-circuits with 422
public static class ValidationFilter
{{
    public static async ValueTask<object?> HandleAsync<T>(
        EndpointFilterInvocationContext ctx,
        EndpointFilterDelegate next)
    {{
        var validator = ctx.HttpContext.RequestServices
            .GetService<IValidator<T>>();
        if (validator is null) return await next(ctx);

        var arg = ctx.Arguments.OfType<T>().First();
        var result = await validator.ValidateAsync(arg);
        if (!result.IsValid)
        {{
            return Results.ValidationProblem(
                result.ToDictionary(),       // field -> string[]
                statusCode: StatusCodes.Status422UnprocessableEntity);
        }}
        return await next(ctx);
    }}
}}

// Apply to an endpoint
app.MapPost("/api/v1/products", CreateProductHandler)
   .AddEndpointFilter(ValidationFilter.HandleAsync<CreateProductRequest>);
""", "Program.cs (validation wiring)")}

<h3>3. Making 422 the default for controllers (if using controllers)</h3>
{C(r"""
builder.Services.AddControllers()
    .ConfigureApiBehaviorOptions(options =>
    {{
        options.InvalidModelStateResponseFactory = ctx =>
        {{
            var errors = ctx.ModelState
                .Where(e => e.Value?.Errors.Count > 0)
                .ToDictionary(
                    kvp => kvp.Key,
                    kvp => kvp.Value!.Errors.Select(e => e.ErrorMessage).ToArray());

            var problem = new ValidationProblemDetails(ctx.ModelState)
            {{
                Status = StatusCodes.Status422UnprocessableEntity,
                Type   = "https://tools.ietf.org/html/rfc9110#section-15.5.21"
            }};
            return new UnprocessableEntityObjectResult(problem)
            {{
                ContentTypes = { "application/problem+json" }
            }};
        }};
    }});
""", "Program.cs (controller 422 config)")}

<h3>4. Async validation for uniqueness</h3>
{C(r"""
// Check for duplicate slug against the database
RuleFor(x => x.Slug)
    .MustAsync(async (slug, ct) =>
    {{
        bool exists = await _repo.SlugExistsAsync(slug, ct);
        return !exists;
    }})
    .WithMessage(x => $"The slug '{{x.Slug}}' is already taken. Please choose another.");
""", "SlugUniquenessRule.cs (excerpt)")}
{warn("MustAsync calls the database on every validation — make sure the query is indexed. For high-throughput endpoints consider checking in the service layer after the synchronous rules pass, so at least the cheap rules fail fast.")}

<h3>5. Testing validators in isolation</h3>
{C(r"""
// Using FluentValidation.TestHelper (also from the FluentValidation NuGet package)
public class CreateProductRequestValidatorTests
{{
    private readonly CreateProductRequestValidator _sut;

    public CreateProductRequestValidatorTests()
    {{
        var repoMock = Substitute.For<IProductRepository>();
        repoMock.CategoryExistsAsync(Arg.Any<int>()).Returns(true);
        _sut = new CreateProductRequestValidator(repoMock);
    }}

    [Fact]
    public async Task Rejects_Empty_Name()
    {{
        var req = new CreateProductRequest("", "some-slug", 299m, 1);
        var result = await _sut.TestValidateAsync(req);
        result.ShouldHaveValidationErrorFor(x => x.Name);
    }}

    [Fact]
    public async Task Rejects_Negative_Price()
    {{
        var req = new CreateProductRequest("Kashmiri Saffron", "kashmiri-saffron", -1m, 1);
        var result = await _sut.TestValidateAsync(req);
        result.ShouldHaveValidationErrorFor(x => x.Price);
    }}

    [Fact]
    public async Task Accepts_Valid_Request()
    {{
        var req = new CreateProductRequest("Kashmiri Saffron", "kashmiri-saffron", 2499m, 1);
        var result = await _sut.TestValidateAsync(req);
        result.ShouldNotHaveAnyValidationErrors();
    }}
}}
""", "CreateProductRequestValidatorTests.cs")}

<h3>6. FluentValidation vs data annotations</h3>
{table(["","FluentValidation","Data annotations"],[
["Rule location","Separate validator class","Attributes on the DTO property"],
["Async rules","Yes (<code>MustAsync</code>)","No"],
["Custom messages","Fluent (<code>WithMessage</code>)","Static string on the attribute"],
["Conditional rules","Yes (<code>When</code>, <code>Unless</code>)","No"],
["Testability","Unit-test the validator class alone","Need to run model binding"],
["Complexity ceiling","Unlimited","Medium"],
["No extra NuGet","No","Yes"]])}
''',
["Registering FluentValidation with <code>AddFluentValidationAutoValidation</code> (old API) — prefer the endpoint filter or manual call.",
"Forgetting to return 422 (not 400) for validation errors.",
"Writing validation logic in the controller action instead of a validator class.",
"MustAsync without an indexed column — will cause N+1 performance problems.",
"Testing the validator only via integration tests — unit-test it directly with <code>TestValidate</code>."],
("40 min", [
    "Write <code>UpdateProductRequestValidator</code> that rejects empty Name and Price ≤ 0.",
    "Add an endpoint filter to the product PUT endpoint and verify a bad request gets a 422 JSON body with <code>errors</code>.",
    "Unit-test both validators with at least three cases each: all-valid, single-field failure, multiple-field failure."
]),
[("How do you inject a repository into a FluentValidation validator?","Declare it as a constructor parameter. When you register with <code>AddValidatorsFromAssemblyContaining</code>, ASP.NET Core's DI container resolves the validator's dependencies automatically."),
("What is the difference between <code>Must</code> and <code>Custom</code>?","<code>Must</code> takes a predicate returning bool and auto-generates one error; <code>Custom</code> (or <code>Custom</code> with the action overload) gives you access to the <code>ValidationContext</code> so you can add multiple errors with custom severity or property names."),
("How do you stop validating a property after the first failure?","Set <code>RuleFor(x =&gt; x.Name).Cascade(CascadeMode.Stop)</code> or configure globally with <code>ValidatorOptions.Global.DefaultRuleLevelCascadeMode = CascadeMode.Stop</code>.")],
[("Basic","What is FluentValidation and why is it preferred over data annotations?","FluentValidation is a .NET library for expressing validation rules in separate validator classes with a fluent API. It supports async rules, conditional rules, complex cross-property checks and is easy to unit-test. Data annotations are simpler and need no extra package, but are limited to static attributes mixed into the model."),
("Basic","How do you return a 422 response from a FluentValidation failure in minimal APIs?","Use <code>Results.ValidationProblem(result.ToDictionary(), statusCode: 422)</code>. This returns a <code>ValidationProblemDetails</code> JSON payload with an <code>errors</code> dictionary."),
("Basic","How do you unit-test a validator?","Instantiate the validator (with any mocked dependencies), call <code>TestValidateAsync(request)</code> and use <code>ShouldHaveValidationErrorFor</code> / <code>ShouldNotHaveAnyValidationErrors</code> from <code>FluentValidation.TestHelper</code>."),
("Intermediate","How would you check for a unique slug in a validator?","Use <code>MustAsync(async (slug, ct) =&gt; !await repo.SlugExistsAsync(slug, ct))</code>. The repository is injected via the validator's constructor. Make sure the slug column is indexed in SQL Server so the check is O(log n), not a table scan."),
("Intermediate","What is the cascade mode and when do you use Stop?","Cascade mode controls what happens when a rule fails. <code>Continue</code> (default in older versions) runs all rules; <code>Stop</code> stops at the first failure on that property. Use Stop to avoid a chain of misleading errors — e.g. don't check format if the field is empty."),
("Intermediate","How does FluentValidation integrate with ASP.NET Core's model validation pipeline?","Register validators with <code>AddValidatorsFromAssemblyContaining</code>. For controllers, calling <code>AddFluentValidationAutoValidation</code> (old) or integrating via <code>InvalidModelStateResponseFactory</code> fires validators as part of model binding. For minimal APIs, use an endpoint filter that resolves <code>IValidator&lt;T&gt;</code> from DI and calls <code>ValidateAsync</code> explicitly.")])

# ================= DAY 4  THU =================
d4 = day(4, "THU", "Pagination, Filtering, Sorting and Search",
"Build a production-quality list endpoint: offset and keyset paging, whitelisted filtering, safe dynamic sorting, full-text search, and a composable IQueryable pipeline.",
[("Offset pagination","Skip N items and take M: <code>OFFSET @skip ROWS FETCH NEXT @take ROWS ONLY</code>. Simple but slow on large offsets."),
("Keyset pagination","Use the last seen key (e.g. last Id or Slug) to anchor the next page. O(log n) for any page; no skipped/duplicated rows during inserts."),
("Cursor","An opaque token (often base-64 encoded) returned by the server representing the position in a dataset; the client passes it back for the next page."),
("PagedResult&lt;T&gt;","A generic envelope: items, current page, page size, total count, total pages, has-next, has-previous."),
("Whitelist filter","Only allow filtering on fields you explicitly permit; prevents clients injecting arbitrary columns."),
("Safe dynamic sort","A <code>Dictionary&lt;string, Expression&lt;Func&lt;T, object&gt;&gt;&gt;</code> mapping allowed field names to LINQ expressions; unknown fields are ignored or return 400."),
("IQueryable composition","Building a LINQ query step-by-step, letting EF Core translate the whole thing to one SQL statement."),
("EF Core .AsSplitQuery()","Splits a query with multiple collection Includes into separate SQL queries to avoid a cartesian explosion."),
("Search","A <code>LIKE %term%</code> or full-text <code>CONTAINS</code> filter against one or more text columns.")],
["Cap page size server-side (e.g. max 100) regardless of what the client asks.",
"Offset pagination is fine up to ~10 k rows; beyond that use keyset or cursor paging.",
"Always sort by a stable, unique column as the last sort key (usually Id) so keyset pages are deterministic.",
"Apply filters before <code>OrderBy</code>; apply <code>OrderBy</code> before <code>Skip/Take</code> — EF Core requires this order.",
"Use a whitelist dictionary for sortable fields — never pass a user string directly to EF's LINQ."],
f'''
<h3>1. PagedResult&lt;T&gt;</h3>
{C(r"""
namespace Catalog.Core.Models;

public record PagedResult<T>(
    IReadOnlyList<T> Items,
    int Page,
    int PageSize,
    long TotalCount)
{{
    public int  TotalPages  => (int)Math.Ceiling(TotalCount / (double)PageSize);
    public bool HasPrevious => Page > 1;
    public bool HasNext     => Page < TotalPages;
}}
""", "PagedResult.cs")}

<h3>2. Query parameters DTO and validation</h3>
{C(r"""
namespace Catalog.Core.Dtos;

public record ProductListQuery
{{
    public int    Page       {{ get; init; }} = 1;
    public int    PageSize   {{ get; init; }} = 20;
    public string? SortBy   {{ get; init; }} = "name";
    public string? SortDir  {{ get; init; }} = "asc";
    public int?   CategoryId {{ get; init; }}
    public bool?  InStock    {{ get; init; }}
    public string? Search    {{ get; init; }}
}}

// Validator
public class ProductListQueryValidator : AbstractValidator<ProductListQuery>
{{
    private static readonly HashSet<string> _allowedSorts =
        ["name", "price", "created-at"];

    public ProductListQueryValidator()
    {{
        RuleFor(x => x.Page).GreaterThanOrEqualTo(1);
        RuleFor(x => x.PageSize).InclusiveBetween(1, 100);

        RuleFor(x => x.SortBy)
            .Must(s => s is null || _allowedSorts.Contains(s.ToLowerInvariant()))
            .WithMessage($"sortBy must be one of: {{string.Join(", ", _allowedSorts)}}.");

        RuleFor(x => x.SortDir)
            .Must(s => s is null || s.ToLowerInvariant() is "asc" or "desc")
            .WithMessage("sortDir must be 'asc' or 'desc'.");
    }}
}}
""", "ProductListQuery.cs")}

<h3>3. IQueryable composition pipeline</h3>
{C(r"""
using System.Linq.Expressions;
using Catalog.Core.Models;
using Catalog.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace Catalog.Infrastructure.Repositories;

public class ProductRepository(CatalogDbContext db) : IProductRepository
{{
    // Safe sort whitelist: field name → EF expression
    private static readonly Dictionary<string, Expression<Func<Product, object>>> _sortMap = new()
    {{
        ["name"]       = p => p.Name,
        ["price"]      = p => (object)p.Price,
        ["created-at"] = p => p.CreatedAt
    }};

    public async Task<PagedResult<Product>> ListAsync(
        ProductListQuery q, CancellationToken ct = default)
    {{
        IQueryable<Product> query = db.Products
            .Include(p => p.Category)
            .Where(p => p.IsActive);               // base filter: only active

        // 1. Filter — whitelist only
        if (q.CategoryId.HasValue)
            query = query.Where(p => p.CategoryId == q.CategoryId.Value);

        if (q.InStock.HasValue)
            query = q.InStock.Value
                ? query.Where(p => p.StockCount > 0)
                : query.Where(p => p.StockCount == 0);

        // 2. Search (LIKE %term%)
        if (!string.IsNullOrWhiteSpace(q.Search))
        {{
            var term = q.Search.Trim();
            query = query.Where(p =>
                EF.Functions.Like(p.Name, $"%{{term}}%") ||
                EF.Functions.Like(p.Description ?? "", $"%{{term}}%"));
        }}

        // 3. Count BEFORE paging (EF translates to SELECT COUNT)
        long total = await query.LongCountAsync(ct);

        // 4. Sort — look up safe expression; fall back to Name
        var sortExpr = _sortMap.GetValueOrDefault(
            q.SortBy?.ToLowerInvariant() ?? "name", _sortMap["name"]);

        query = q.SortDir?.ToLowerInvariant() == "desc"
            ? query.OrderByDescending(sortExpr).ThenBy(p => p.Id)   // tie-break with Id
            : query.OrderBy(sortExpr).ThenBy(p => p.Id);

        // 5. Offset pagination — cap page size server-side
        int pageSize = Math.Min(q.PageSize, 100);
        int skip     = (q.Page - 1) * pageSize;

        var items = await query
            .Skip(skip)
            .Take(pageSize)
            .AsNoTracking()
            .ToListAsync(ct);

        return new PagedResult<Product>(items, q.Page, pageSize, total);
    }}
}}
""", "ProductRepository.cs")}

<h3>4. Keyset / cursor paging</h3>
{C(r"""
// After getting page 1, the client sends the last seen slug as afterSlug.
// No OFFSET: EF translates this to WHERE Slug > @afterSlug ORDER BY Slug, Id
public async Task<List<Product>> ListKeysetAsync(
    string? afterSlug, int pageSize = 20, CancellationToken ct = default)
{{
    pageSize = Math.Min(pageSize, 100);
    IQueryable<Product> query = db.Products
        .Where(p => p.IsActive)
        .OrderBy(p => p.Name).ThenBy(p => p.Id);   // stable compound sort

    if (afterSlug is not null)
        query = query.Where(p => string.Compare(p.Slug, afterSlug) > 0);

    return await query.Take(pageSize).AsNoTracking().ToListAsync(ct);
}}

// Response includes the last slug so the client can pass it back
public record KeysetPage<T>(IReadOnlyList<T> Items, string? NextCursor, bool HasMore);
""", "ProductRepository.cs (keyset)")}
{tip("For keyset pagination on large datasets, index the cursor column. In EF Core 8+ you can also use <code>ExecuteQuery</code> with raw SQL for maximum control.")}

<h3>5. The endpoint</h3>
{C(r"""
app.MapGet("/api/v1/products", async (
    [AsParameters] ProductListQuery q,
    IProductRepository repo,
    IMapper mapper,
    CancellationToken ct) =>
{{
    var page = await repo.ListAsync(q, ct);
    return Results.Ok(new
    {{
        items      = page.Items.Select(mapper.Map<ProductResponse>),
        page       = page.Page,
        pageSize   = page.PageSize,
        totalCount = page.TotalCount,
        totalPages = page.TotalPages,
        hasNext    = page.HasNext,
        hasPrevious= page.HasPrevious
    }});
}})
.AddEndpointFilter(ValidationFilter.HandleAsync<ProductListQuery>);
""", "ProductsEndpoints.cs")}
''',
["Passing user sort strings directly to <code>OrderBy</code> — always use a whitelist map.",
"Forgetting to cap page size — a client requesting pageSize=100000 will DoS your DB.",
"Counting after pagination instead of before — you lose total count.",
"Using keyset with a non-unique column — duplicates cause rows to be skipped.",
"Applying <code>OrderBy</code> before <code>Where</code> — EF will complain and SQL Server may ignore the order."],
("45 min", [
    "Add <code>ListAsync</code> to your Catalog repository with offset paging, search on <code>Name</code>, and sort by <code>name</code> or <code>price</code>.",
    "Call <code>GET /api/v1/products?page=1&amp;pageSize=5&amp;sortBy=price&amp;sortDir=desc&amp;search=chai</code> and log the SQL EF Core generates.",
    "Add a keyset endpoint <code>GET /api/v1/products/hot?after=&amp;pageSize=5</code> and verify the second page picks up after the cursor."
]),
[("Why is a ThenBy(p => p.Id) needed after the main sort?","Without a tiebreaker, two products with the same price (or name) could appear in different orders on different pages, causing items to be skipped or duplicated. Id is unique so it makes the sort deterministic."),
("How does EF Core translate IQueryable filter chains into SQL?","EF Core builds an expression tree from each LINQ operation. When you call ToListAsync, it translates the whole tree into a single SQL statement. The filters and projections go into the WHERE and SELECT clauses; Skip/Take become OFFSET/FETCH NEXT."),
("What is the downside of offset paging at high offsets?","SQL Server must read and discard all rows before the offset, so OFFSET 10000 FETCH NEXT 20 reads 10020 rows. For deep pages use keyset or cursor paging.")],
[("Basic","What is offset pagination and what are its limits?","Offset pagination uses Skip/Take (SQL: OFFSET n ROWS FETCH NEXT m ROWS ONLY) to jump to a page. It is simple and supports random access to any page, but performance degrades with large offsets because the database reads and discards all preceding rows."),
("Basic","Why cap page size on the server?","A malicious or buggy client could request pageSize=1000000, returning millions of rows, exhausting memory and DB connections. The server must enforce a maximum (commonly 100–500) regardless of the client's request."),
("Basic","What is a whitelist sort map and why use it?","A Dictionary mapping allowed field names to LINQ expressions. The user sends a sort field name; the server looks it up in the map. Unknown fields return 400. Never pass a user-supplied string directly to <code>OrderBy</code> — that is an injection risk."),
("Intermediate","Explain keyset pagination and when to use it.","Keyset (cursor) paging anchors to the last seen value of the sort column: WHERE col &gt; @lastSeen ORDER BY col TAKE n. The database uses an index seek (O(log n)) regardless of page depth, never reads skipped rows, and handles inserts/deletes between pages correctly. Use it for large tables, infinite scroll and real-time feeds."),
("Intermediate","How do you get the total count efficiently with EF Core?","Call <code>query.LongCountAsync()</code> on the filtered but un-paged IQueryable before applying Skip/Take. EF Core translates this to SELECT COUNT(*) using the same WHERE clause, so it runs in one extra DB round-trip."),
("Intermediate","What is IQueryable composition and how does it help?","You build up a LINQ expression tree by chaining Where, OrderBy, Skip and Take without hitting the database. EF Core translates the entire tree into a single SQL statement when you call ToListAsync. This is more efficient than fetching all rows into memory and filtering in C#.")])

# ================= DAY 5  FRI =================
d5 = day(5, "FRI", "API Versioning, OpenAPI Polish and Typed Client Generation",
"Version your API without breaking existing clients, polish your OpenAPI spec, and understand how to generate a typed HTTP client from it.",
[("API versioning","Letting multiple versions of an endpoint coexist so old clients keep working while new clients use the latest."),
("URL-segment versioning","Version in the URI path: <code>/api/v1/products</code> vs <code>/api/v2/products</code>. Most discoverable."),
("Query-string versioning","Version as a parameter: <code>/api/products?api-version=1.0</code>."),
("Header versioning","Version in a custom header: <code>X-Api-Version: 1.0</code>. Clean URIs but invisible in browser address bar."),
("Asp.Versioning.Http","The official Microsoft versioning NuGet package for minimal APIs and controllers."),
("Deprecation","Marking an older version as sunset — clients get a <code>Sunset</code> response header or a <code>deprecated</code> flag in OpenAPI."),
("OpenAPI / Swagger","A machine-readable specification of your API's endpoints, models and authentication."),
("Swashbuckle","The classic .NET package that generates OpenAPI from reflection. Available for .NET 8."),
("Microsoft.AspNetCore.OpenApi",".NET 9 built-in OpenAPI support, without needing Swashbuckle. Add with <code>builder.Services.AddOpenApi()</code>."),
("NSwag","Generates TypeScript, C# or other client code from an OpenAPI spec."),
("Kiota","Microsoft's client generator: creates strongly-typed, fluent HTTP client code from an OpenAPI spec.")],
[".NET 8: use Swashbuckle or NSwag for OpenAPI. .NET 9 adds built-in <code>Microsoft.AspNetCore.OpenApi</code> as an alternative.",
"Always keep at least one version stable; never break a released version — add a new one instead.",
"Mark old versions <code>[Deprecated]</code> and set a <code>Sunset</code> date.",
"Annotate endpoints with <code>Produces&lt;T&gt;</code> and <code>ProducesProblem</code> so the OpenAPI spec is accurate.",
"Use Kiota or NSwag to generate a typed client — avoids hand-rolling <code>HttpClient</code> boilerplate."],
f'''
<h3>1. Installing and configuring Asp.Versioning.Http</h3>
{C(r"""
// dotnet add package Asp.Versioning.Http
// dotnet add package Asp.Versioning.Mvc.ApiExplorer   (for OpenAPI integration)

// Program.cs
builder.Services
    .AddApiVersioning(options =>
    {{
        options.DefaultApiVersion            = new ApiVersion(1, 0);
        options.AssumeDefaultVersionWhenUnspecified = true;
        options.ReportApiVersions            = true;   // adds api-supported-versions header
    }})
    .AddApiExplorer(options =>
    {{
        options.GroupNameFormat           = "'v'VVV";   // "v1", "v2"
        options.SubstituteApiVersionInUrl = true;
    }});
""", "Program.cs (versioning setup)")}

<h3>2. URL-segment versioning with minimal APIs</h3>
{C(r"""
var v1 = app.NewVersionedApi("Products");

RouteGroupBuilder v1Group = v1.MapGroup("/api/v1/products")
    .HasApiVersion(1, 0)
    .WithTags("Products");

RouteGroupBuilder v2Group = v1.MapGroup("/api/v2/products")
    .HasApiVersion(2, 0)
    .WithTags("Products");

// V1 endpoint
v1Group.MapGet("/", GetProductsV1);
v1Group.MapGet("/{{id:int}}", GetProductByIdV1);
v1Group.MapPost("/", CreateProductV1);
v1Group.MapPut("/{{id:int}}", UpdateProductV1);
v1Group.MapDelete("/{{id:int}}", DeleteProductV1);

// V2 adds a slug lookup and richer response
v2Group.MapGet("/", GetProductsV2);
v2Group.MapGet("/{{id:int}}", GetProductByIdV2);
v2Group.MapGet("/by-slug/{{slug}}", GetProductBySlugV2);
v2Group.MapPost("/", CreateProductV2);
""", "ProductEndpoints.cs")}

<h3>3. Deprecating a version</h3>
{C(r"""
// Mark v1 as deprecated — still works, but callers see a warning
v1Group.HasDeprecatedApiVersion(1, 0);

// Or on a controller
[ApiVersion("1.0", Deprecated = true)]
[Route("api/v{{version:apiVersion}}/products")]
public class ProductsV1Controller : ControllerBase {{ ... }}

// Consumers receive headers:
// api-supported-versions: 1.0, 2.0
// api-deprecated-versions: 1.0
""", "DeprecationExample.cs")}

<h3>4. OpenAPI polish (.NET 8 — Swashbuckle)</h3>
{C(r"""
// dotnet add package Swashbuckle.AspNetCore

builder.Services.AddSwaggerGen(c =>
{{
    c.SwaggerDoc("v1", new OpenApiInfo
    {{
        Title       = "Catalog API",
        Version     = "v1",
        Description = "Product catalog for an Indian e-commerce platform."
    }});
    // Add JWT auth to swagger UI
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {{
        Type = SecuritySchemeType.Http,
        Scheme = "bearer",
        BearerFormat = "JWT"
    }});
}});

// Annotate endpoints with response types (improves spec accuracy)
app.MapGet("/api/v1/products/{{id:int}}", GetById)
   .Produces<ProductResponse>(200)
   .ProducesProblem(404)
   .ProducesProblem(500)
   .WithName("GetProductById")
   .WithSummary("Get a single product by integer id");
""", "SwaggerSetup.cs")}

<h3>5. .NET 9 built-in OpenAPI (alternative to Swashbuckle)</h3>
{C(r"""
// .NET 9 — Microsoft.AspNetCore.OpenApi is included in the framework
// No extra NuGet required; replaces Swashbuckle for new .NET 9 projects.

builder.Services.AddOpenApi();      // adds the OpenAPI document service

app.MapOpenApi();                   // serves /openapi/v1.json

// Optionally add Swagger UI from a separate lightweight package
app.UseSwaggerUI(options =>
    options.SwaggerEndpoint("/openapi/v1.json", "Catalog API v1"));

// Annotate endpoints identically to Swashbuckle
app.MapGet("/api/v1/products", GetProducts)
   .WithOpenApi(op =>
   {{
       op.Summary = "List products with filtering and paging";
       return op;
   }});
""", "OpenApiSetup_Net9.cs")}
{tip(".NET 9's built-in OpenAPI doesn't yet ship a Swagger UI — add <code>Scalar.AspNetCore</code> or <code>Swashbuckle.AspNetCore.SwaggerUI</code> for the interactive UI in .NET 9.")}

<h3>6. Generating a typed client with Kiota</h3>
{C(r"""
# Install the Kiota CLI tool
dotnet tool install --global Microsoft.OpenApi.Kiota

# Generate a C# client from your running API's OpenAPI spec
kiota generate \
  --openapi https://localhost:5001/openapi/v1.json \
  --language CSharp \
  --class-name CatalogApiClient \
  --namespace-name CatalogClient \
  --output ./generated

# In your consumer project (e.g. a Blazor frontend or worker service):
# dotnet add package Microsoft.Kiota.Bundle
var client = new CatalogApiClient(
    new HttpClientRequestAdapter(new AnonymousAuthenticationProvider())
    {{
        BaseUrl = "https://api.mystore.in"
    }});

var products = await client.Api.V1.Products.GetAsync();
""", "kiota-client-setup.sh", lang="bash")}
''',
["Breaking a released API version — always add a new version rather than changing existing endpoints.",
"Forgetting to set <code>AssumeDefaultVersionWhenUnspecified = true</code> — existing clients without a version header break.",
"Not annotating <code>Produces&lt;T&gt;</code> — the OpenAPI spec shows <code>string</code> for all responses.",
"Running Kiota against an incomplete or unannotated spec — garbage in, garbage out.",
"Using Swashbuckle in a .NET 9 project without checking if the built-in OpenAPI support covers your needs first."],
("40 min", [
    "Add <code>Asp.Versioning.Http</code> to the Catalog API and move all endpoints under <code>/api/v1/</code>.",
    "Add Swashbuckle (or use .NET 9 built-in OpenAPI if on .NET 9), annotate all endpoints with <code>Produces&lt;T&gt;</code> and open the Swagger UI.",
    "Run Kiota against your spec and inspect the generated <code>CatalogApiClient</code> class."
]),
[("What does <code>AssumeDefaultVersionWhenUnspecified</code> do?","When a request arrives with no version indicator, it is treated as the default version. Without this, unversioned clients get a 400 error immediately after versioning is enabled."),
("What is the difference between Swashbuckle and Microsoft.AspNetCore.OpenApi?","Swashbuckle is a third-party NuGet package that generates OpenAPI via reflection, works in .NET 6/7/8/9. Microsoft.AspNetCore.OpenApi is a first-party package added in .NET 9 that is lighter and ships with the framework, but lacks a built-in Swagger UI."),
("Why use a generated client instead of HttpClient directly?","A generated client (Kiota, NSwag) gives you strongly typed request/response models, URL building, and serialisation for free, reducing boilerplate and ensuring the client stays in sync with the server contract.")],
[("Basic","Why do you need API versioning?","Once an API endpoint is published, changing its contract (renaming fields, removing endpoints, changing response shapes) breaks existing clients. Versioning lets you introduce breaking changes in a new version while old clients continue using the previous version undisturbed."),
("Basic","What are the three main versioning strategies?","URL segment (<code>/api/v1/products</code>), query string (<code>/api/products?api-version=1.0</code>), and header (<code>X-Api-Version: 1</code>). URL segment is most discoverable and cache-friendly; header versioning keeps URIs clean."),
("Basic","What is OpenAPI?","A language-agnostic, machine-readable specification (JSON or YAML) that describes an HTTP API's endpoints, request/response models, authentication requirements and error responses. Tools like Swagger UI render it interactively; Kiota and NSwag generate client code from it."),
("Intermediate","How does Asp.Versioning.Http work in minimal APIs?","You call <code>app.NewVersionedApi()</code> to create a versioned API group, then map route groups with <code>.HasApiVersion()</code>. The middleware reads the version from the URL segment, query string or header (depending on configuration) and routes to the matching handler."),
("Intermediate","What is Kiota and how does it differ from NSwag?","Both generate typed HTTP client code from an OpenAPI spec. NSwag has been around longer, generates simpler client code and also generates the server side. Kiota is a newer Microsoft open-source tool that follows the Graph SDK pattern — it generates a fluent request builder for each path and handles pagination and error types consistently."),
("Intermediate","How do you mark an API version as deprecated without breaking it?","In Asp.Versioning.Http, set <code>Deprecated = true</code> on the <code>ApiVersion</code> attribute (controllers) or call <code>.HasDeprecatedApiVersion()</code> on the route group (minimal APIs). The versioning middleware adds <code>api-deprecated-versions</code> response headers and the OpenAPI spec marks the operations as deprecated.")])

# ================= DAY 6  SAT =================
d6 = day(6, "SAT", "Catalog API — Full Project",
"Build a complete Indian product catalog REST API with Api/Core/Infrastructure layers, EF Core, FluentValidation, ProblemDetails, pagination, filtering, sorting and versioning. Budget: ~4 hours.",
[("Catalog API","The weekend micro-project: a fully layered REST API for browsing and managing Indian kurtas, spices, chai and similar products."),
("Api layer","ASP.NET Core project: endpoints, middleware, DI wiring, DTOs."),
("Core layer","Class library: domain models, interfaces, DTOs, validators, service contracts."),
("Infrastructure layer","Class library: EF Core DbContext, migrations, repository implementations."),
("Product","Domain entity with Id, Name, Slug, Description, Price, StockCount, CategoryId, BrandId, IsActive."),
("Category","Hierarchical entity — a category can have a parent, enabling a tree."),
("Brand","Simple lookup entity: Id, Name, Slug.")],
["Install FluentValidation, Mapster, EF Core + SQL Server provider from NuGet.",
"Run migrations before starting the API: <code>dotnet ef migrations add InitialSchema</code>.",
"Keep the API layer thin: DTOs in and out, service calls in the middle.",
"Use <code>AsNoTracking()</code> on all read queries.",
"Test every curl example below; look at the SQL EF logs for pagination and keyset queries."],
f'''
<h3>Scaffold</h3>
{C(r"""
# Create the solution
dotnet new sln -n Catalog
dotnet new webapi -n Catalog.Api        --framework net8.0 -o src/Catalog.Api
dotnet new classlib -n Catalog.Core      --framework net8.0 -o src/Catalog.Core
dotnet new classlib -n Catalog.Infrastructure --framework net8.0 -o src/Catalog.Infrastructure

dotnet sln add src/Catalog.Api/Catalog.Api.csproj
dotnet sln add src/Catalog.Core/Catalog.Core.csproj
dotnet sln add src/Catalog.Infrastructure/Catalog.Infrastructure.csproj

# References
dotnet add src/Catalog.Api reference src/Catalog.Core src/Catalog.Infrastructure
dotnet add src/Catalog.Infrastructure reference src/Catalog.Core

# NuGet
dotnet add src/Catalog.Infrastructure package Microsoft.EntityFrameworkCore.SqlServer --version 8.0.0
dotnet add src/Catalog.Infrastructure package Microsoft.EntityFrameworkCore.Tools     --version 8.0.0
dotnet add src/Catalog.Api              package Microsoft.EntityFrameworkCore.Design  --version 8.0.0
dotnet add src/Catalog.Core             package FluentValidation                      --version 11.9.0
dotnet add src/Catalog.Api              package FluentValidation.AspNetCore           --version 11.9.0
dotnet add src/Catalog.Core             package Mapster                               --version 7.4.0
dotnet add src/Catalog.Api              package Swashbuckle.AspNetCore                --version 6.6.2
dotnet add src/Catalog.Api              package Asp.Versioning.Http                  --version 8.1.0
dotnet add src/Catalog.Api              package Asp.Versioning.Mvc.ApiExplorer       --version 8.1.0
""", "scaffold.sh", lang="bash")}

<h3>Folder layout</h3>
{C(r"""
src/
  Catalog.Core/
    Models/     Product.cs  Category.cs  Brand.cs
    Dtos/       ProductDtos.cs  CategoryDtos.cs  BrandDtos.cs
    Interfaces/ IProductRepository.cs  ICategoryRepository.cs
    Validators/ CreateProductRequestValidator.cs
  Catalog.Infrastructure/
    Data/       CatalogDbContext.cs
    Repositories/  ProductRepository.cs  CategoryRepository.cs
  Catalog.Api/
    Endpoints/  ProductEndpoints.cs  CategoryEndpoints.cs
    Middleware/  GlobalExceptionHandler.cs  ValidationFilter.cs
    Program.cs
""", "folder-structure.txt", lang="text")}

<h3>Domain models</h3>
{C(r"""
namespace Catalog.Core.Models;

public class Brand
{{
    public int    Id   {{ get; set; }}
    public string Name {{ get; set; }} = string.Empty;
    public string Slug {{ get; set; }} = string.Empty;
}}

public class Category
{{
    public int      Id       {{ get; set; }}
    public string   Name     {{ get; set; }} = string.Empty;
    public string   Slug     {{ get; set; }} = string.Empty;
    public int?     ParentId {{ get; set; }}

    public Category? Parent   {{ get; set; }}
    public List<Category> Children {{ get; set; }} = [];
    public List<Product>  Products {{ get; set; }} = [];
}}

public class Product
{{
    public int      Id          {{ get; set; }}
    public string   Name        {{ get; set; }} = string.Empty;
    public string   Slug        {{ get; set; }} = string.Empty;
    public string?  Description {{ get; set; }}
    public decimal  Price       {{ get; set; }}
    public int      StockCount  {{ get; set; }}
    public bool     IsActive    {{ get; set; }} = true;
    public int      CategoryId  {{ get; set; }}
    public int?     BrandId     {{ get; set; }}
    public DateTimeOffset CreatedAt {{ get; set; }} = DateTimeOffset.UtcNow;
    public DateTimeOffset? UpdatedAt {{ get; set; }}

    public Category Category {{ get; set; }} = null!;
    public Brand?   Brand    {{ get; set; }}
}}
""", "Models.cs")}

<h3>DbContext</h3>
{C(r"""
using Catalog.Core.Models;
using Microsoft.EntityFrameworkCore;

namespace Catalog.Infrastructure.Data;

public class CatalogDbContext(DbContextOptions<CatalogDbContext> options)
    : DbContext(options)
{{
    public DbSet<Product>  Products   {{ get; set; }}
    public DbSet<Category> Categories {{ get; set; }}
    public DbSet<Brand>    Brands     {{ get; set; }}

    protected override void OnModelCreating(ModelBuilder mb)
    {{
        mb.Entity<Product>(e =>
        {{
            e.HasKey(p => p.Id);
            e.Property(p => p.Name).HasMaxLength(200).IsRequired();
            e.Property(p => p.Slug).HasMaxLength(100).IsRequired();
            e.HasIndex(p => p.Slug).IsUnique();              // unique slug index
            e.Property(p => p.Price).HasColumnType("decimal(18,2)");
            e.HasOne(p => p.Category).WithMany(c => c.Products)
             .HasForeignKey(p => p.CategoryId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(p => p.Brand).WithMany()
             .HasForeignKey(p => p.BrandId).OnDelete(DeleteBehavior.SetNull).IsRequired(false);
        }});

        mb.Entity<Category>(e =>
        {{
            e.HasKey(c => c.Id);
            e.Property(c => c.Name).HasMaxLength(100).IsRequired();
            e.Property(c => c.Slug).HasMaxLength(100).IsRequired();
            e.HasIndex(c => c.Slug).IsUnique();
            e.HasOne(c => c.Parent).WithMany(c => c.Children)
             .HasForeignKey(c => c.ParentId).OnDelete(DeleteBehavior.Restrict).IsRequired(false);
        }});

        mb.Entity<Brand>(e =>
        {{
            e.HasKey(b => b.Id);
            e.Property(b => b.Name).HasMaxLength(100).IsRequired();
            e.Property(b => b.Slug).HasMaxLength(100).IsRequired();
            e.HasIndex(b => b.Slug).IsUnique();
        }});

        // Seed data — Indian product catalog
        mb.Entity<Brand>().HasData(
            new Brand {{ Id = 1, Name = "FabIndia", Slug = "fabindia" }},
            new Brand {{ Id = 2, Name = "Nykaa Fashion", Slug = "nykaa-fashion" }},
            new Brand {{ Id = 3, Name = "Teabox", Slug = "teabox" }});

        mb.Entity<Category>().HasData(
            new Category {{ Id = 1, Name = "Clothing",  Slug = "clothing",  ParentId = null }},
            new Category {{ Id = 2, Name = "Kurtas",    Slug = "kurtas",    ParentId = 1 }},
            new Category {{ Id = 3, Name = "Groceries", Slug = "groceries", ParentId = null }},
            new Category {{ Id = 4, Name = "Spices",    Slug = "spices",    ParentId = 3 }},
            new Category {{ Id = 5, Name = "Tea & Coffee", Slug = "tea-coffee", ParentId = 3 }}
        );

        mb.Entity<Product>().HasData(
            new Product {{ Id=1, Name="Men's Linen Kurta", Slug="mens-linen-kurta",
                Price=1299m, StockCount=50, CategoryId=2, BrandId=1,
                Description="Comfortable summer kurta in natural linen." }},
            new Product {{ Id=2, Name="Kashmiri Saffron", Slug="kashmiri-saffron",
                Price=2499m, StockCount=20, CategoryId=4,
                Description="Pure Grade A saffron, 1g pouch." }},
            new Product {{ Id=3, Name="Darjeeling First Flush Tea", Slug="darjeeling-first-flush",
                Price=599m,  StockCount=100, CategoryId=5, BrandId=3,
                Description="Single estate, light and floral." }},
            new Product {{ Id=4, Name="Garam Masala Blend", Slug="garam-masala-blend",
                Price=199m,  StockCount=200, CategoryId=4,
                Description="Family recipe, 100g tin." }},
            new Product {{ Id=5, Name="Ikat Print Kurta", Slug="ikat-print-kurta",
                Price=1799m, StockCount=0,  CategoryId=2, BrandId=2,
                Description="Handwoven Odisha ikat — currently out of stock." }}
        );
    }}
}}
""", "CatalogDbContext.cs")}

<h3>Program.cs</h3>
{C(r"""
using Catalog.Infrastructure.Data;
using Catalog.Core.Validators;
using FluentValidation;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// EF Core
builder.Services.AddDbContext<CatalogDbContext>(opt =>
    opt.UseSqlServer(builder.Configuration.GetConnectionString("Catalog"))
       .EnableSensitiveDataLogging(builder.Environment.IsDevelopment()));

// FluentValidation
builder.Services.AddValidatorsFromAssemblyContaining<CreateProductRequestValidator>();

// Mapster (global config loaded via TypeAdapterConfig.GlobalSettings)
builder.Services.AddSingleton(TypeAdapterConfig.GlobalSettings);
builder.Services.AddScoped<IMapper, ServiceMapper>();

// Versioning
builder.Services
    .AddApiVersioning(o =>
    {{
        o.DefaultApiVersion = new ApiVersion(1, 0);
        o.AssumeDefaultVersionWhenUnspecified = true;
        o.ReportApiVersions = true;
    }})
    .AddApiExplorer(o =>
    {{
        o.GroupNameFormat = "'v'VVV";
        o.SubstituteApiVersionInUrl = true;
    }});

// OpenAPI / Swagger
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// ProblemDetails + exception handler
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

var app = builder.Build();

app.UseExceptionHandler();

if (app.Environment.IsDevelopment())
{{
    app.UseSwagger();
    app.UseSwaggerUI();

    // Auto-migrate + seed on startup in dev
    using var scope = app.Services.CreateScope();
    var db = scope.ServiceProvider.GetRequiredService<CatalogDbContext>();
    db.Database.Migrate();
}}

// Register endpoints
app.MapProductEndpoints();
app.MapCategoryEndpoints();

app.Run();
""", "Program.cs")}

<h3>Product endpoints</h3>
{C(r"""
using Catalog.Core.Dtos;
using Catalog.Infrastructure.Repositories;
using MapsterMapper;

namespace Catalog.Api.Endpoints;

public static class ProductEndpoints
{{
    public static void MapProductEndpoints(this WebApplication app)
    {{
        var v1 = app.NewVersionedApi("Products");
        var group = v1.MapGroup("/api/v1/products")
                      .HasApiVersion(1, 0)
                      .WithTags("Products");

        group.MapGet("/", ListProducts)
            .Produces<PagedResult<ProductResponse>>()
            .WithSummary("List products with paging, filtering, sorting and search");

        group.MapGet("/{{id:int}}", GetById)
            .Produces<ProductResponse>()
            .ProducesProblem(404)
            .WithName("GetProductById");

        group.MapGet("/by-slug/{{slug}}", GetBySlug)
            .Produces<ProductResponse>()
            .ProducesProblem(404);

        group.MapPost("/", CreateProduct)
            .Produces<ProductResponse>(StatusCodes.Status201Created)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .AddEndpointFilter(ValidationFilter.HandleAsync<CreateProductRequest>);

        group.MapPut("/{{id:int}}", UpdateProduct)
            .Produces<ProductResponse>()
            .ProducesProblem(404)
            .ProducesProblem(StatusCodes.Status422UnprocessableEntity)
            .AddEndpointFilter(ValidationFilter.HandleAsync<UpdateProductRequest>);

        group.MapDelete("/{{id:int}}", DeleteProduct)
            .Produces(StatusCodes.Status204NoContent)
            .ProducesProblem(404);
    }}

    // --- handlers (injected via parameter binding) ---

    static async Task<IResult> ListProducts(
        [AsParameters] ProductListQuery q,
        IProductRepository repo, IMapper mapper)
    {{
        var page = await repo.ListAsync(q);
        return Results.Ok(new
        {{
            items       = page.Items.Select(p => mapper.Map<ProductResponse>(p)),
            page        = page.Page,
            pageSize    = page.PageSize,
            totalCount  = page.TotalCount,
            totalPages  = page.TotalPages,
            hasNext     = page.HasNext,
            hasPrevious = page.HasPrevious
        }});
    }}

    static async Task<IResult> GetById(
        int id, IProductRepository repo, IMapper mapper)
    {{
        var p = await repo.GetByIdAsync(id);
        return p is null
            ? Results.Problem($"Product {{id}} was not found.", statusCode: 404)
            : Results.Ok(mapper.Map<ProductResponse>(p));
    }}

    static async Task<IResult> GetBySlug(
        string slug, IProductRepository repo, IMapper mapper)
    {{
        var p = await repo.GetBySlugAsync(slug);
        return p is null
            ? Results.Problem($"Product '{{slug}}' was not found.", statusCode: 404)
            : Results.Ok(mapper.Map<ProductResponse>(p));
    }}

    static async Task<IResult> CreateProduct(
        CreateProductRequest req, IProductRepository repo, IMapper mapper)
    {{
        if (await repo.SlugExistsAsync(req.Slug))
            return Results.Problem(
                detail: $"The slug '{{req.Slug}}' is already taken.",
                statusCode: StatusCodes.Status409Conflict);

        var product = mapper.Map<Product>(req);
        await repo.AddAsync(product);
        var resp = mapper.Map<ProductResponse>(product);
        return Results.Created($"/api/v1/products/{{product.Id}}", resp);
    }}

    static async Task<IResult> UpdateProduct(
        int id, UpdateProductRequest req,
        IProductRepository repo, IMapper mapper)
    {{
        var product = await repo.GetByIdAsync(id);
        if (product is null)
            return Results.Problem($"Product {{id}} was not found.", statusCode: 404);

        mapper.Map(req, product);
        product.UpdatedAt = DateTimeOffset.UtcNow;
        await repo.UpdateAsync(product);
        return Results.Ok(mapper.Map<ProductResponse>(product));
    }}

    static async Task<IResult> DeleteProduct(int id, IProductRepository repo)
    {{
        var product = await repo.GetByIdAsync(id);
        if (product is null)
            return Results.Problem($"Product {{id}} was not found.", statusCode: 404);
        await repo.DeleteAsync(product);
        return Results.NoContent();
    }}
}}
""", "ProductEndpoints.cs")}

<h3>Category tree endpoint</h3>
{C(r"""
// Returns the full category hierarchy in one shot
app.MapGet("/api/v1/categories/tree", async (CatalogDbContext db) =>
{{
    var roots = await db.Categories
        .Include(c => c.Children)
        .Where(c => c.ParentId == null)
        .AsNoTracking()
        .ToListAsync();

    return Results.Ok(roots.Select(ToCategoryTree));
}})
.WithTags("Categories")
.Produces<IEnumerable<CategoryTreeResponse>>();

static CategoryTreeResponse ToCategoryTree(Category c) =>
    new(c.Id, c.Name, c.Slug, c.Children.Select(ToCategoryTree).ToList());

public record CategoryTreeResponse(
    int Id, string Name, string Slug,
    IReadOnlyList<CategoryTreeResponse> Children);
""", "CategoryEndpoints.cs (excerpt)")}

<h3>Run migrations and start</h3>
{C(r"""
# Start SQL Server in Docker
docker run -e ACCEPT_EULA=Y -e SA_PASSWORD=YourStrong!Passw0rd \
  -p 1433:1433 --name catalog-sql -d \
  mcr.microsoft.com/mssql/server:2022-latest

# Add connection string to appsettings.Development.json
{{
  "ConnectionStrings": {{
    "Catalog": "Server=localhost,1433;Database=CatalogDb;User=sa;Password=YourStrong!Passw0rd;TrustServerCertificate=True;"
  }}
}}

# EF migrations
dotnet ef migrations add InitialSchema -p src/Catalog.Infrastructure -s src/Catalog.Api
dotnet ef database update            -p src/Catalog.Infrastructure -s src/Catalog.Api

dotnet run --project src/Catalog.Api
""", "run.sh", lang="bash")}

<h3>curl examples</h3>
{C(r"""
# List first page
curl -s https://localhost:5001/api/v1/products | jq .

# Filter to kurtas category (id=2), sort by price desc, page 1
curl -s "https://localhost:5001/api/v1/products?categoryId=2&sortBy=price&sortDir=desc" | jq .

# Search for chai / tea
curl -s "https://localhost:5001/api/v1/products?search=chai" | jq .

# Only in-stock products
curl -s "https://localhost:5001/api/v1/products?inStock=true" | jq .

# Get by slug
curl -s https://localhost:5001/api/v1/products/by-slug/kashmiri-saffron | jq .

# Create a new product
curl -s -X POST https://localhost:5001/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{{"name":"Masala Chai Blend","slug":"masala-chai-blend","price":349,"categoryId":5,"stockCount":80}}' | jq .

# Update price
curl -s -X PUT https://localhost:5001/api/v1/products/3 \
  -H "Content-Type: application/json" \
  -d '{{"name":"Darjeeling First Flush Tea","price":649}}' | jq .

# Delete a product
curl -s -X DELETE https://localhost:5001/api/v1/products/5

# Category tree
curl -s https://localhost:5001/api/v1/categories/tree | jq .
""", "curl-examples.sh", lang="bash")}

<h3>Stretch goals</h3>
{ul([
    "Add a <code>BrandId</code> filter to the product list endpoint.",
    "Implement the keyset paging endpoint <code>GET /api/v1/products/hot?after=&amp;pageSize=5</code>.",
    "Add image URL support: <code>ImageUrl</code> on Product, serve static files from <code>wwwroot/images/</code>.",
    "Write an xUnit integration test using <code>WebApplicationFactory&lt;Program&gt;</code> against the real endpoint.",
    "Add Redis output caching (<code>builder.Services.AddOutputCache()</code>) on the list endpoint."
])}
''',
iqs=[("Basic","What is the purpose of the Core/Infrastructure/Api layer split?","Core holds domain models, interfaces and business rules with no framework dependencies — it can be unit-tested without ASP.NET Core or EF Core. Infrastructure implements the interfaces against real storage. Api is the thin HTTP layer. This makes Core portable and maximally testable."),
("Basic","Why are unique index constraints on Slug important for the API?","Slugs are used in SEO-friendly URLs. A database-level unique index enforces that no two products share a slug, complementing the application-level 409 Conflict check. If the application check races (concurrent creates), the DB constraint is the safety net."),
("Intermediate","How does EF Core handle the self-referencing Category hierarchy?","You configure a self-referencing relationship with <code>HasOne(c => c.Parent).WithMany(c => c.Children).HasForeignKey(c => c.ParentId)</code>. Loading the full tree requires either recursive Includes or a raw recursive CTE. For small catalogs, eager loading two levels is fine; for deep trees, prefer a raw SQL closure table."),
("Intermediate","How do you prevent the category tree endpoint from causing a cycle serialisation error?","The <code>CategoryTreeResponse</code> record maps children recursively, projecting to DTOs rather than returning EF entities. No navigation properties from EF entities reach the serialiser, so there is no cycle.")])

# ================= DAY 7  SUN =================
d7 = day(7, "SUN", "Dapper Read Endpoint, Try-to-Break and Week Review",
"Add a Dapper hot-list endpoint, honestly measure EF vs Dapper, try to break your API with malformed inputs, write the README, commit and review the week.",
[("Dapper","A lightweight .NET micro-ORM: runs raw SQL and maps rows to objects with minimal overhead. NuGet: <code>Dapper</code>."),
("CQRS-lite","A pattern where reads (queries) and writes (commands) use different code paths — here EF Core for writes, Dapper for a read-heavy hot path."),
("N+1 problem","Fetching a list of N products then executing N additional queries for related data. Fix with Include() in EF or a JOIN in Dapper."),
("Connection string","The secret that belongs in <code>appsettings.Development.json</code> (or user secrets) — never hardcoded or committed."),
("Hot path","A code path called very frequently; worth optimising more carefully than the average endpoint.")],
["Dapper is not automatically better than EF Core — measure before switching.",
"Use Dapper for hand-tuned read queries; keep EF Core for writes where the change tracker earns its keep.",
"Always parameterise queries in Dapper — <code>WHERE Id = @id</code> never string interpolation.",
"The sandbox has no SQL Server: test these snippets on your Docker container.",
"Commit with a meaningful message, not just 'initial commit'."],
f'''
<h3>1. Dapper hot-list endpoint</h3>
<p>Add a <code>GET /api/v1/products/hot</code> endpoint that returns the 10 cheapest in-stock products.  EF Core would handle this fine, but this endpoint will be called on the homepage of a high-traffic site, so we hand-tune the SQL.</p>
{C(r"""
using Dapper;
using Microsoft.Data.SqlClient;

namespace Catalog.Infrastructure.Repositories;

public class ProductReadRepository(IConfiguration config)
{{
    private SqlConnection OpenConnection() =>
        new(config.GetConnectionString("Catalog"));

    // Hand-tuned read query: no EF overhead, one round-trip, neatly parameterised
    public async Task<IReadOnlyList<HotProductDto>> GetHotListAsync(int take = 10)
    {{
        const string sql = QQQ
            SELECT TOP (@take)
                   p.Id,
                   p.Name,
                   p.Slug,
                   p.Price,
                   c.Name  AS CategoryName,
                   b.Name  AS BrandName
            FROM   Products  p
            JOIN   Categories c ON c.Id = p.CategoryId
            LEFT   JOIN Brands b ON b.Id = p.BrandId
            WHERE  p.IsActive = 1
              AND  p.StockCount > 0
            ORDER  BY p.Price ASC
        QQQ;

        await using var conn = OpenConnection();
        var rows = await conn.QueryAsync<HotProductDto>(sql, new {{ take }});
        return rows.ToList();
    }}
}}

public record HotProductDto(
    int     Id,
    string  Name,
    string  Slug,
    decimal Price,
    string  CategoryName,
    string? BrandName);
""", "ProductReadRepository.cs")}
{C(r"""
// Register the Dapper repository in Program.cs
builder.Services.AddScoped<ProductReadRepository>();

// Endpoint
app.MapGet("/api/v1/products/hot", async (ProductReadRepository repo) =>
{{
    var items = await repo.GetHotListAsync(10);
    return Results.Ok(items);
}})
.WithTags("Products")
.Produces<IReadOnlyList<HotProductDto>>();
""", "Program.cs (hot endpoint)")}

<h3>2. Honest EF Core vs Dapper comparison</h3>
{table(["","EF Core (tracked)","EF Core (AsNoTracking)","Dapper"],[
["Cold-start overhead","High (model build)","High","None"],
["Warm query overhead","Medium (expression tree)","Lower","Minimal"],
["Change tracking","Yes","No","No"],
["Migrations / schema","Yes (Migrations)","Yes","Manual DDL"],
["N+1 guard","Include() / AsSplitQuery()","Same","You write the JOIN"],
["Complex dynamic queries","IQueryable builder","Same","String building (risk of SQL injection if not careful)"],
["Best for","CRUD writes, relationships","Simple reads","High-throughput reads, hand-tuned SQL"]])}
{tip("Benchmark with BenchmarkDotNet before switching to Dapper.  On most CRUD endpoints with a local SQL Server the difference is under 0.5 ms per request — not worth the reduced safety.  Where it matters: bulk reads of thousands of rows, tight latency SLAs, complex aggregation queries.")}

<h3>3. Try to break it</h3>
{table(["Attack","Expected behaviour","Actual? (verify)"],[
["<code>GET /api/v1/products?page=0</code>","422 — page must be ≥ 1",""],
["<code>GET /api/v1/products?pageSize=5000</code>","Server caps at 100; returns 100 or fewer rows",""],
["<code>GET /api/v1/products?sortBy=DROP TABLE Products--</code>","422 — sortBy must be one of the allowed values",""],
["<code>GET /api/v1/products?sortBy=evil</code>","422 — not in whitelist",""],
["<code>POST /api/v1/products</code> body with duplicate slug","409 Conflict with ProblemDetails JSON",""],
["<code>POST /api/v1/products</code> empty name","422 with errors.Name field",""],
["<code>POST /api/v1/products</code> price = -50","422 with errors.Price field",""],
["<code>GET /api/v1/products/999999</code>","404 with ProblemDetails JSON",""],
["<code>DELETE /api/v1/products/1</code> twice","204 on first, 404 on second",""],
["<code>GET /api/v1/products?search=&lt;script&gt;alert(1)&lt;/script&gt;</code>","Returns empty list (no match); no XSS — JSON response not rendered as HTML",""]])}

<h3>4. README template</h3>
{C(r"""
# Catalog API — Week 18

## Purpose
REST API for an Indian e-commerce product catalog: kurtas, spices, chai and more.

## Stack
- .NET 8 / ASP.NET Core minimal APIs
- EF Core 8 + SQL Server 2022
- FluentValidation 11 · Mapster 7 · Swashbuckle 6 · Asp.Versioning.Http 8

## Quick start
```bash
# 1. Start SQL Server
docker run -e ACCEPT_EULA=Y -e SA_PASSWORD=YourStrong!Passw0rd \
  -p 1433:1433 --name catalog-sql -d mcr.microsoft.com/mssql/server:2022-latest

# 2. Apply migrations
dotnet ef database update -p src/Catalog.Infrastructure -s src/Catalog.Api

# 3. Run
dotnet run --project src/Catalog.Api
# → https://localhost:5001/swagger
```

## Key endpoints
| Method | Path                                 | Description            |
|--------|--------------------------------------|------------------------|
| GET    | /api/v1/products                     | List with paging+filter|
| GET    | /api/v1/products/{id}                | Get by id              |
| GET    | /api/v1/products/by-slug/{slug}      | Get by slug            |
| GET    | /api/v1/products/hot                 | Hot list (Dapper)      |
| POST   | /api/v1/products                     | Create                 |
| PUT    | /api/v1/products/{id}                | Full update            |
| DELETE | /api/v1/products/{id}                | Delete                 |
| GET    | /api/v1/categories/tree              | Category hierarchy     |

## Notes
- AutoMapper was considered but not used due to 2025 licensing changes.
- Mapster handles DTO mapping; FluentValidation handles request validation.
- Dapper powers the /hot endpoint only; EF Core handles all writes.
""", "README.md", lang="text")}

<h3>5. Git commit</h3>
{C(r"""
cd Catalog
git init
git add .
git commit -m "Week 18: Catalog REST API

- REST principles: ProblemDetails (RFC 9457), status codes, 201+Location
- Request/response DTOs with Mapster; AutoMapper licensing note
- FluentValidation with async slug-uniqueness check; endpoint filter returns 422
- PagedResult<T>: offset paging with server cap, keyset endpoint
- Whitelisted sort map; search with EF.Functions.Like
- Asp.Versioning.Http v1 URL-segment versioning; Swashbuckle OpenAPI
- Dapper hot-list read endpoint; EF vs Dapper comparison
- Seed data: kurtas, saffron, chai, spices (Indian catalog)"
""", "git-commit.sh", lang="bash")}

<h3>Week 18 checklist</h3>
{ul([
    "Can explain the difference between safe and idempotent HTTP methods.",
    "Can describe what a 201, 204, 409 and 422 response means.",
    "Can implement <code>IExceptionHandler</code> and return ProblemDetails on 500.",
    "Understand over-posting and can prevent it with request DTOs.",
    "Can choose between manual mapping, Mapster and AutoMapper (with the licensing caveat).",
    "Can write FluentValidation rules including async uniqueness checks.",
    "Can build an IQueryable pipeline with offset paging, whitelisted sort and search.",
    "Can explain keyset paging and when to prefer it over offset.",
    "Can add URL-segment API versioning with Asp.Versioning.Http.",
    "Can annotate endpoints for OpenAPI and serve Swagger UI.",
    "Know .NET 9 ships built-in Microsoft.AspNetCore.OpenApi.",
    "Can add a Dapper read endpoint alongside EF Core writes (CQRS-lite).",
    "Have run the try-to-break table against the live API.",
    "README and git commit done."
])}

<h3>Quiz — predict the output / does it compile?</h3>
<details><summary>Q1. What HTTP status code should a successful POST that creates a new product return, and what header is required?</summary>
{C(r"""
// Answer: 201 Created with a Location header pointing to the new resource URI.
// Results.Created("/api/v1/products/42", dto) sets both automatically.
""")}<b>201 + Location.</b> Without the Location header the client doesn't know where to find the new resource.</details>

<details><summary>Q2. Does this compile and what does it do?</summary>
{C(r"""
var sortMap = new Dictionary<string, Expression<Func<Product, object>>>()
{{
    ["price"] = p => (object)p.Price
}};
string field = "evil; DROP TABLE Products--";
var expr = sortMap.GetValueOrDefault(field, sortMap["price"]);
IQueryable<Product> q = db.Products.OrderBy(expr);
""")}<b>Compiles and is safe.</b> The user's string is only used as a dictionary key — it never reaches SQL. Unknown keys fall back to the "price" expression. No injection risk.</details>

<details><summary>Q3. What is wrong with this validator?</summary>
{C(r"""
public class MyValidator : AbstractValidator<CreateProductRequest>
{{
    public MyValidator()
    {{
        RuleFor(x => x.Slug)
            .MustAsync(async (slug, ct) =>
            {{
                using var conn = new SqlConnection("Server=.;...");
                return !await conn.ExecuteScalarAsync<bool>(
                    $"SELECT COUNT(1) FROM Products WHERE Slug = '{{slug}}'");
            }});
    }}
}}
""")}<b>SQL injection.</b> The slug is interpolated directly into the SQL string. Use a parameterised query: <code>WHERE Slug = @slug</code> with an anonymous <code>new {{ slug }}</code> parameter.</details>

<details><summary>Q4. What response does this endpoint return for a valid request and what is missing?</summary>
{C(r"""
app.MapPost("/api/v1/products", async (CreateProductRequest req, IProductRepository repo) =>
{{
    var p = await repo.AddAsync(req);
    return Results.Ok(p);
}});
""")}<b>200 OK.</b> Should be 201 Created with a Location header. Use <code>Results.Created($"/api/v1/products/{{p.Id}}", p)</code>.</details>

<details><summary>Q5. The /api/v1/products?page=0&amp;sortBy=evil request reaches the endpoint. What happens if the endpoint filter is attached?</summary>
{C(r"""
app.MapGet("/api/v1/products", ListProducts)
   .AddEndpointFilter(ValidationFilter.HandleAsync<ProductListQuery>);
// ProductListQueryValidator rejects page < 1 and unknown sortBy values
""")}<b>422 Unprocessable Content</b> with a JSON errors body listing both failures — page must be ≥ 1 and sortBy must be one of the allowed values. The endpoint handler never runs.</details>

<div class="note tip"><b>Next week:</b> Week 19 — Cross-cutting concerns: middleware pipeline, logging with Serilog structured JSON, health checks, rate limiting, output caching and CORS.  Micro-project: Blog API with per-endpoint rate limits and structured request logs.</div>
''',
iqs=[("Basic","What is CQRS-lite and why use it?","A lightweight application of CQRS: reads (queries) and writes (commands) use separate code paths. Here EF Core handles writes — benefiting from the change tracker, model validation and migrations — while Dapper handles a performance-sensitive read endpoint with hand-written SQL. Full CQRS with separate read/write databases (from Week 21 onwards) is the more advanced form."),
("Basic","How do you prevent SQL injection in Dapper?","Always use parameterised queries with anonymous objects: <code>conn.QueryAsync&lt;T&gt;(sql, new {{ id }})</code>. Never interpolate user input into SQL strings. Dapper's parameterisation maps C# type names to SQL parameter names by convention."),
("Intermediate","When would you choose Dapper over EF Core for a read endpoint?","When you need fine-grained SQL control — complex aggregations, window functions, CTEs, or heavily tuned joins. Also when profiling shows EF Core's expression translation or query plan is suboptimal. For standard CRUD and simple reads, EF Core's AsNoTracking is usually fast enough and far safer."),
("Intermediate","What is the N+1 problem in EF Core and how do you fix it?","If you fetch N products then access <code>product.Category</code> inside a loop, EF Core fires one query for the list plus N queries for the categories — N+1 total. Fix with <code>.Include(p =&gt; p.Category)</code> in the original query, which generates a JOIN, or with <code>AsSplitQuery()</code> for multiple collection Includes.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","REST Principles and HTTP Semantics","REST &amp; HTTP","URIs, verbs, idempotency, status codes, ProblemDetails RFC 9457, HATEOAS awareness.","2 hrs"),
 (2,"TUE","DTOs, Mapping and Records","DTOs &amp; Mapping","Over-posting, request/response DTOs, manual mapping vs Mapster vs AutoMapper (licensing note), records.","2 hrs"),
 (3,"WED","FluentValidation","FluentValidation","Rules, async uniqueness, DI injection, endpoint-filter wiring, 422 field errors vs data annotations.","2 hrs"),
 (4,"THU","Pagination, Filtering, Sorting &amp; Search","Paging &amp; Filtering","Offset + keyset paging, whitelisted sort map, IQueryable composition, search, PagedResult&lt;T&gt;.","2 hrs"),
 (5,"FRI","API Versioning, OpenAPI &amp; Typed Clients","Versioning &amp; OpenAPI","Asp.Versioning.Http, URL-segment versioning, deprecation, Swashbuckle, .NET 9 built-in OpenAPI, Kiota.","2 hrs"),
 (6,"SAT","Catalog API — Full Project","Project: Catalog API","Api/Core/Infrastructure, Product/Category/Brand, EF Core, CRUD, paging, FluentValidation, ProblemDetails.","4 hrs"),
 (7,"SUN","Dapper Read, Try-to-Break &amp; Review","Review &amp; Dapper","Dapper hot-list endpoint, EF vs Dapper honest comparison, try-to-break table, README, checklist, quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week18.html", 18,
      "Week 18 — REST API Design", "Phase 2", "~18 hrs",
      ["Phase 2 · Week 18 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "Catalog API"],
      "Every HTTP endpoint you build is a contract with your callers.  This week covers REST principles and HTTP semantics, DTO design and mapping (including the 2025 AutoMapper licensing note), expressive FluentValidation with async rules, production-quality pagination and filtering, API versioning, and OpenAPI polish.  Saturday builds a fully layered Catalog API for Indian products — kurtas, saffron, chai and spices — and Sunday adds a Dapper hot-list endpoint and a try-to-break session.",
      cards, days)
print("built")
