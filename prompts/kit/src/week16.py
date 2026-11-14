import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Loading related data: Include, ThenInclude, filtered Include, explicit and lazy loading",
"Extend last week's StoreDb with customers and orders, then load related data on purpose — eagerly, explicitly or lazily — and read the SQL each choice produces.",
[("Navigation property","A property that points to related entities: a reference (<code>Order.Customer</code>) or a collection (<code>Customer.Orders</code>)."),
("Related data","Rows in other tables reached through foreign keys. EF Core does <b>not</b> load it unless you ask."),
("Eager loading","Loading related data in the same query with <code>Include</code> / <code>ThenInclude</code>."),
("Include","Adds one navigation to the query: <code>Orders.Include(o =&gt; o.Customer)</code>. Translates to a JOIN."),
("ThenInclude","Continues an include path one level deeper: <code>Include(o =&gt; o.Lines).ThenInclude(l =&gt; l.Product)</code>."),
("Filtered Include","EF Core 5+: <code>Include(c =&gt; c.Orders.Where(...).OrderBy(...).Take(n))</code> loads only some children. Allowed operators: Where, OrderBy(Descending), ThenBy(Descending), Skip, Take."),
("Explicit loading","Loading a navigation later, on demand, for an entity already in memory: <code>db.Entry(c).Collection(x =&gt; x.Orders).LoadAsync()</code>."),
("Lazy loading","Navigations load automatically the first time code reads them. Needs proxies (<code>Microsoft.EntityFrameworkCore.Proxies</code>) or an injected <code>ILazyLoader</code>."),
("Proxy","A runtime-generated subclass of your entity that overrides <code>virtual</code> navigations to trigger loading."),
("Relationship fix-up","EF Core automatically connects tracked entities to each other via their keys, even if you never included the navigation."),
("IsLoaded","<code>db.Entry(e).Collection(...).IsLoaded</code> — whether EF thinks a navigation has been fully loaded."),
("Required vs optional navigation","Required (non-nullable FK) produces <code>INNER JOIN</code>; optional (nullable FK) produces <code>LEFT JOIN</code>."),
("ToQueryString()","EF Core 5+: returns the SQL a LINQ query will run, without running it. Ideal for learning and debugging.")],
["No Include = navigation stays <code>null</code> (reference) or empty (collection) — unless fix-up or lazy loading fills it.",
"Every Include of a collection multiplies rows in a single query. Two collections = rows of A × rows of B (Tuesday).",
"Filtered Include filters only the included children, never the parent rows.",
"Explicit loading is a deliberate extra query. Lazy loading is a <i>hidden</i> extra query — that's the danger.",
"Read the SQL for every new query you write: <code>LogTo</code> or <code>ToQueryString()</code>.",
"Prefer async (<code>ToListAsync</code>, <code>LoadAsync</code>) in apps; sync versions exist but block a thread."],
f'''
<h3>1. Extend the StoreDb model: customers, orders, order lines</h3>
<p>Last week's <code>Store.Core</code> had <code>Category</code> and <code>Product</code>. Add three entities. An order belongs to one customer and has many lines; each line points to one product and stores the <b>price at the time of ordering</b> (today's product price may change later).</p>
{C(r"""
namespace Store.Core.Entities;

public class Customer
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public required string Email { get; set; }
    public string City { get; set; } = "";
    public List<Order> Orders { get; set; } = [];
}

public enum OrderStatus { Pending, Paid, Shipped, Delivered, Cancelled }

public class Order
{
    public int Id { get; set; }
    public int CustomerId { get; set; }                 // required FK (non-nullable int)
    public Customer Customer { get; set; } = null!;     // "null!" = EF fills it when loaded
    public DateTime OrderDateUtc { get; set; }
    public OrderStatus Status { get; set; }
    public List<OrderLine> Lines { get; set; } = [];
}

public class OrderLine
{
    public int Id { get; set; }
    public int OrderId { get; set; }
    public Order Order { get; set; } = null!;
    public int ProductId { get; set; }
    public Product Product { get; set; } = null!;
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }              // snapshot of Product.Price when ordered
}
""", "Store.Core/Entities/Orders.cs")}
{C(r"""
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Store.Core.Entities;

namespace Store.Data.Configurations;

public class CustomerConfiguration : IEntityTypeConfiguration<Customer>
{
    public void Configure(EntityTypeBuilder<Customer> b)
    {
        b.Property(c => c.Name).HasMaxLength(100);
        b.Property(c => c.Email).HasMaxLength(200);
        b.HasIndex(c => c.Email).IsUnique();
        b.Property(c => c.City).HasMaxLength(60);
    }
}

public class OrderConfiguration : IEntityTypeConfiguration<Order>
{
    public void Configure(EntityTypeBuilder<Order> b)
    {
        b.HasOne(o => o.Customer).WithMany(c => c.Orders)
         .HasForeignKey(o => o.CustomerId)
         .OnDelete(DeleteBehavior.Restrict);           // never lose order history by deleting a customer
        b.HasMany(o => o.Lines).WithOne(l => l.Order)
         .HasForeignKey(l => l.OrderId)
         .OnDelete(DeleteBehavior.Cascade);            // lines live and die with their order
        b.HasIndex(o => o.OrderDateUtc);
    }
}

public class OrderLineConfiguration : IEntityTypeConfiguration<OrderLine>
{
    public void Configure(EntityTypeBuilder<OrderLine> b)
    {
        b.Property(l => l.UnitPrice).HasPrecision(18, 2);
        b.HasOne(l => l.Product).WithMany()
         .HasForeignKey(l => l.ProductId)
         .OnDelete(DeleteBehavior.Restrict);
    }
}
""", "Store.Data/Configurations/OrderConfigurations.cs")}
{C(r"""
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Store.Core.Entities;

namespace Store.Data;

public class StoreDbContext(DbContextOptions<StoreDbContext> options) : DbContext(options)
{
    public DbSet<Category> Categories => Set<Category>();
    public DbSet<Product> Products => Set<Product>();
    public DbSet<Customer> Customers => Set<Customer>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
        => modelBuilder.ApplyConfigurationsFromAssembly(typeof(StoreDbContext).Assembly);
}

// A tiny helper for this week's console experiments
public static class Db
{
    public const string ConnectionString =
        "Server=localhost,1433;Database=StoreDb;User Id=sa;Password=Dev@Pass123;TrustServerCertificate=True";

    public static StoreDbContext Create(bool logSql = true)
    {
        var builder = new DbContextOptionsBuilder<StoreDbContext>().UseSqlServer(ConnectionString);
        if (logSql)   // print only the SQL commands, not every EF log line
            builder.LogTo(Console.WriteLine, [DbLoggerCategory.Database.Command.Name], LogLevel.Information);
        return new StoreDbContext(builder.Options);
    }
}
""", "Store.Data/StoreDbContext.cs")}
{C(r"""
dotnet ef migrations add AddCustomersAndOrders -p Store.Data -s Store.App
dotnet ef database update -p Store.Data -s Store.App
""", lang="bash")}
<p>Seed a few rows (Asha Rao from Pune, Ravi Kumar from Chennai, Meena Iyer from Bengaluru, each with 2–3 orders) with a quick script or SQL <code>INSERT</code>s so the queries below return something.</p>

<h3>2. Eager loading: Include and ThenInclude</h3>
<p>Without Include, EF Core loads only the columns of the entity you queried. Navigations stay empty — this surprises everyone once.</p>
{C(r"""
await using var db = Db.Create();

var plain = await db.Orders.FirstAsync(o => o.Id == 1);
Console.WriteLine(plain.Customer is null);      // True  — not loaded (no Include, nothing tracked yet)
Console.WriteLine(plain.Lines.Count);           // 0     — empty list from the initialiser, NOT "no lines"

var order = await db.Orders
    .Include(o => o.Customer)                    // reference navigation
    .Include(o => o.Lines)                       // collection navigation
        .ThenInclude(l => l.Product)             // one level deeper, from each line
            .ThenInclude(p => p.Category)        // and deeper again
    .FirstAsync(o => o.Id == 1);

Console.WriteLine($"{order.Customer.Name}, {order.Customer.City}");    // Asha Rao, Pune
foreach (var l in order.Lines)
    Console.WriteLine($"  {l.Product.Name} ({l.Product.Category.Name}) × {l.Quantity} @ ₹{l.UnitPrice}");
//   Basmati Rice 5kg (Grocery) × 2 @ ₹649.00
//   Steel Water Bottle (Home) × 1 @ ₹399.00
""", "LoadingDemo.cs")}
<p>Note: by the time we run the second query, order 1 is already tracked from the first query, and EF <i>reuses that same instance</i> — Include fills in its navigations. That is relationship fix-up at work.</p>
<p>To include two separate paths from the same collection, repeat the <code>Include</code>:</p>
{C(r"""
var orders = await db.Orders
    .Include(o => o.Lines).ThenInclude(l => l.Product)
    .Include(o => o.Lines).ThenInclude(l => l.Order)       // second path, starts again at Lines
    .ToListAsync();

// String-based include works too (handy when building paths dynamically):
var same = await db.Orders.Include("Lines.Product").ToListAsync();
""")}
<h4>The SQL it produces</h4>
<p>Print it without running anything using <code>ToQueryString()</code>:</p>
{C(r"""
var query = db.Orders
    .Include(o => o.Customer)
    .Include(o => o.Lines).ThenInclude(l => l.Product)
    .Where(o => o.Id == 1);
Console.WriteLine(query.ToQueryString());
""")}
{C(r"""
-- Example output (EF Core 8, formatted; aliases can differ slightly by version)
DECLARE @__p_0 int = 1;   -- not emitted: EF inlines the constant 1 here; shown for a parameterised version

SELECT [o].[Id], [o].[CustomerId], [o].[OrderDateUtc], [o].[Status],
       [c].[Id], [c].[City], [c].[Email], [c].[Name],
       [s].[Id], [s].[OrderId], [s].[ProductId], [s].[Quantity], [s].[UnitPrice],
       [s].[Id0], [s].[CategoryId], [s].[Name], [s].[Price], [s].[Sku], [s].[Stock]
FROM [Orders] AS [o]
INNER JOIN [Customers] AS [c] ON [o].[CustomerId] = [c].[Id]           -- required reference → INNER JOIN
LEFT JOIN (
    SELECT [l].[Id], [l].[OrderId], [l].[ProductId], [l].[Quantity], [l].[UnitPrice],
           [p].[Id] AS [Id0], [p].[CategoryId], [p].[Name], [p].[Price], [p].[Sku], [p].[Stock]
    FROM [OrderLines] AS [l]
    INNER JOIN [Products] AS [p] ON [l].[ProductId] = [p].[Id]
) AS [s] ON [o].[Id] = [s].[OrderId]                                    -- collection → LEFT JOIN
WHERE [o].[Id] = 1
ORDER BY [o].[Id], [c].[Id], [s].[Id]                                   -- keys, so EF can stitch rows back
""", "Generated SQL (example)", lang="sql")}
{table(["What you wrote","What SQL Server sees"],[
["<code>Include</code> of a required reference","<code>INNER JOIN</code>"],
["<code>Include</code> of an optional reference","<code>LEFT JOIN</code>"],
["<code>Include</code> of a collection","<code>LEFT JOIN</code> (orders with no lines must still appear) + <code>ORDER BY</code> keys"],
["<code>ThenInclude</code> inside a collection","A subquery joined in, as above"],
["Several collection Includes","Several LEFT JOINs → row multiplication (Tuesday: split queries)"]])}
{tip("The trailing <code>ORDER BY</code> on keys is how EF Core turns one flat, repeated result set back into an object graph: it reads rows in key order and starts a new Order object whenever <code>o.Id</code> changes.")}

<h3>3. Filtered Include (EF Core 5+)</h3>
<p>Load customers with only their <b>last three paid orders</b>, newest first:</p>
{C(r"""
var customers = await db.Customers
    .Where(c => c.City == "Pune")
    .Include(c => c.Orders
        .Where(o => o.Status == OrderStatus.Paid)
        .OrderByDescending(o => o.OrderDateUtc)
        .Take(3))
    .ToListAsync();

foreach (var c in customers)
    Console.WriteLine($"{c.Name}: {c.Orders.Count} recent paid orders");
// Asha Rao: 3 recent paid orders
// Kiran Patil: 1 recent paid orders     ← customers with no matching orders are still returned
""")}
{warn("Filtered Include filters the <i>children</i>, never the parents — customers without paid orders still come back with an empty list. To filter parents, add a normal <code>Where(c =&gt; c.Orders.Any(...))</code>.", "Gotcha")}
{warn("With a <b>tracking</b> query, fix-up can add children you filtered out: if an earlier query in the same context already loaded Asha's cancelled orders, they appear in <code>c.Orders</code> too. Use a fresh context or <code>AsNoTracking()</code> when the filtered collection must be exact. You also can't apply two <i>different</i> filters to the same navigation in one query.", "Gotcha")}

<h3>4. Explicit loading</h3>
<p>Load the entity first, decide later whether you need its relations. Useful when the decision depends on the data (e.g. only load lines for high-value orders), or for a single entity in a detail screen.</p>
{C(r"""
var customer = await db.Customers.SingleAsync(c => c.Email == "ravi.kumar@example.in");

// Collection navigation
await db.Entry(customer).Collection(c => c.Orders).LoadAsync();
Console.WriteLine(customer.Orders.Count);                                   // 3

// Reference navigation
var anOrder = customer.Orders[0];
await db.Entry(anOrder).Reference(o => o.Customer).LoadAsync();              // already loaded → no SQL sent?
Console.WriteLine(db.Entry(anOrder).Reference(o => o.Customer).IsLoaded);    // True

// Query() lets you filter or aggregate WITHOUT loading the whole collection
int pending = await db.Entry(customer)
    .Collection(c => c.Orders)
    .Query()                                                    // IQueryable<Order> for this customer only
    .CountAsync(o => o.Status == OrderStatus.Pending);
Console.WriteLine($"Pending: {pending}");                       // Pending: 1  → SELECT COUNT(*) ... WHERE CustomerId = @p

// Load only some children into the navigation
await db.Entry(customer).Collection(c => c.Orders).Query()
    .Where(o => o.OrderDateUtc >= new DateTime(2026, 1, 1))
    .Include(o => o.Lines)
    .LoadAsync();
""", "ExplicitLoading.cs")}
<p>About the reference line: <code>anOrder.Customer</code> was already connected by fix-up when we loaded the orders, so <code>IsLoaded</code> is true. <code>Load</code> on a navigation that's already marked loaded does nothing; on one that isn't, it always sends SQL.</p>

<h3>5. Lazy loading — and why most teams turn it off</h3>
<p>With lazy-loading proxies, reading a navigation triggers a query automatically. Setup:</p>
{C(r"""
dotnet add Store.Data package Microsoft.EntityFrameworkCore.Proxies
""", lang="bash")}
{C(r"""
// 1) Turn it on
var options = new DbContextOptionsBuilder<StoreDbContext>()
    .UseLazyLoadingProxies()
    .UseSqlServer(Db.ConnectionString)
    .Options;

// 2) Every navigation must be virtual, and entity classes public and NOT sealed
public class Customer
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public required string Email { get; set; }
    public string City { get; set; } = "";
    public virtual List<Order> Orders { get; set; } = [];
}

public class Order
{
    public int Id { get; set; }
    public int CustomerId { get; set; }
    public virtual Customer Customer { get; set; } = null!;
    public virtual List<OrderLine> Lines { get; set; } = [];
    // ...
}
""", "Lazy loading setup (fragment)")}
{C(r"""
await using var db = new StoreDbContext(options);
var customers = await db.Customers.ToListAsync();        // 1 query

foreach (var c in customers)
{
    // Each access to c.Orders silently runs: SELECT ... FROM Orders WHERE CustomerId = @p
    Console.WriteLine($"{c.Name}: {c.Orders.Count} orders");
}
// 50 customers → 1 + 50 = 51 round trips. This is the N+1 problem (Tuesday).
""")}
{table(["Risk","What happens"],[
["Hidden N+1 queries","Loops over entities fire one query per item; fine on 5 dev rows, painful on 5,000 production rows."],
["Disposed context","Touching a navigation after the DbContext is disposed: EF can't load it. By default this is reported as an error (an <code>InvalidOperationException</code> from the <code>LazyLoadOnDisposedContextWarning</code>)."],
["Serialization storms","Returning entities from a Web API: the JSON serializer walks every navigation → loads the whole graph, or loops on cycles."],
["Sync I/O","Lazy loads are synchronous database calls, even inside async methods."],
["Design constraints","Every navigation <code>virtual</code>, classes unsealed; proxies are a different runtime type (<code>Castle.Proxies.CustomerProxy</code>)."]])}
<p>Without proxies, an entity can take an <code>ILazyLoader</code> in its constructor and call <code>loader.Load(this, ref _orders)</code> in the getter — same behaviour, more plumbing, and your domain class now references EF Core. Rarely worth it.</p>

<h3>6. Choosing a strategy</h3>
{table(["Strategy","Queries","Best for","Watch out for"],[
["Eager (<code>Include</code>)","1 (or 1 per collection with split queries)","You know up front what the screen/endpoint needs","Too many collection includes → cartesian explosion"],
["Filtered Include","1","\"Top N children per parent\"","Fix-up adding extra children in tracking queries"],
["Explicit (<code>Entry().Load</code>)","1 extra per call, visible in code","Conditional or one-off loads; counting via <code>Query()</code>","Calling it inside a loop = N+1 you wrote yourself"],
["Lazy (proxies)","1 extra per navigation touched, invisible","Quick prototypes, desktop apps with long-lived contexts","N+1, disposed-context errors, serializers"],
["Projection (<code>Select</code>)","1, only needed columns","Read-only APIs and reports (Tuesday)","Not tracked — can't be updated and saved"]])}
''',
["Expecting <code>order.Customer</code> to be filled without an Include — then \"fixing\" the NullReferenceException with lazy loading.",
"Reading <code>order.Lines.Count == 0</code> as \"no lines\" when the collection was simply never loaded.",
"Including whole graphs \"just in case\" — every Include adds JOINs and columns.",
"Assuming filtered Include filters the parent rows.",
"Turning on lazy loading in a Web API and returning entities directly from controllers."],
("35 min", ["Add Customer, Order and OrderLine to your StoreDb, create the migration and seed 3 customers with 2–3 orders each (Indian names, cities, ₹ prices).",
"Write three queries for \"order 1 with its customer and products\": Include/ThenInclude, explicit loading, and lazy loading. Log the SQL for each with <code>LogTo</code> and count the round trips.",
"Using a filtered Include, list each Pune customer with their two most recent orders; then use <code>Entry(...).Collection(...).Query().SumAsync(...)</code> to print each customer's lifetime spend without loading their orders."]),
[("Why might <code>order.Lines</code> be empty even though the order has lines in the database?","EF Core doesn't load navigations unless asked. Without Include, explicit or lazy loading (or fix-up from earlier queries in the same context), the collection is just the empty list from the property initialiser."),
("What does filtered Include filter?","Only the included child collection. The parent rows are unaffected; use a separate Where on the parent query to filter parents."),
("What two things does lazy loading with proxies require on your entity classes?","Navigation properties must be <code>virtual</code> and the classes must be public and not sealed, so Castle can generate a subclass that overrides them. You also need the Proxies package and <code>UseLazyLoadingProxies()</code>.")],
[("Basic","What are the three ways to load related data in EF Core?","Eager loading with Include/ThenInclude in the same query; explicit loading with <code>context.Entry(e).Collection(...)/Reference(...).Load()</code> later on demand; and lazy loading, where reading a navigation triggers a query automatically via proxies or ILazyLoader. A fourth common option is projecting with Select, which pulls related columns without loading entities."),
("Basic","What SQL does Include produce?","A JOIN in the same statement: INNER JOIN for a required reference, LEFT JOIN for optional references and collections. For collections EF also adds ORDER BY on the keys so it can rebuild the object graph from the flat rows."),
("Intermediate","What is filtered Include and what are its limitations?","Since EF Core 5 you can write <code>Include(c =&gt; c.Orders.Where(...).OrderBy(...).Take(n))</code>. Only Where, OrderBy/ThenBy (and Descending), Skip and Take are allowed. It filters children, not parents; the same navigation can't be included with two different filters; and in tracking queries, fix-up can add already-tracked children that don't match the filter."),
("Intermediate","Why do many teams disable lazy loading?","It hides database calls behind property access, so loops cause N+1 queries, it fails after the context is disposed, serializers trigger loading of entire graphs, and the loads are synchronous. Eager loading or projections make the data access explicit and reviewable."),
("Intermediate","What is relationship fix-up?","When entities are tracked by the same DbContext, EF Core connects their navigations automatically using foreign keys. If you load orders and, separately, their customers, each <code>order.Customer</code> gets set even though you never included it. It's useful, but it can also make navigations look 'loaded' unexpectedly."),
("Intermediate","How would you count a customer's pending orders without loading all their orders?","Explicit loading's <code>Query()</code>: <code>db.Entry(customer).Collection(c =&gt; c.Orders).Query().CountAsync(o =&gt; o.Status == OrderStatus.Pending)</code>, which sends a single <code>SELECT COUNT(*) ... WHERE CustomerId = @p AND Status = ...</code>. Or simply <code>db.Orders.CountAsync(o =&gt; o.CustomerId == id &amp;&amp; ...)</code>.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "N+1, AsNoTracking, projections to DTOs, AsSplitQuery vs single query",
"Spot and fix N+1 queries, reduce memory with no-tracking reads, project only the columns you need, and decide when to split a multi-collection query.",
[("N+1 problem","A query that returns N rows, then fires one more query per row to load a navigation — 1 + N round trips instead of 1."),
("LogTo","<code>DbContextOptionsBuilder.LogTo(Console.WriteLine, ...)</code> routes EF's log to the console so you can count SQL statements."),
("AsNoTracking","Instructs EF Core not to add entities to the change tracker. Faster and uses less memory for read-only queries."),
("AsNoTrackingWithIdentityResolution","Like AsNoTracking but still de-duplicates objects: the same Customer row in multiple Order rows becomes one C# object."),
("Identity resolution","EF's guarantee that one database row maps to exactly one object instance in a tracking query."),
("Projection","A <code>Select(x =&gt; new Dto { ... })</code> that asks the database for only the columns you name, skipping navigation loading entirely."),
("DTO (Data Transfer Object)","A plain class or record carrying only the data needed by a caller — no navigations, no change tracker."),
("AsSplitQuery","EF Core 5+: Tells EF to run one SELECT per included collection instead of one big JOIN, avoiding cartesian explosion."),
("Cartesian explosion","When a query joins two or more collections and the row count multiplies: an order with 5 lines and 5 tags yields 25 rows per order."),
("UseQueryTrackingBehavior","A context-level default for tracking; override per-query with AsTracking() or AsNoTracking().")],
["Run every new query through LogTo and count the SQL statements — the number should not surprise you.",
"<code>AsNoTracking</code> skips snapshot creation; benchmarks typically show 2–5× less memory and 10–30% faster reads for read-only paths.",
"Projection to a DTO usually beats Include: it generates a narrower SELECT and returns no tracked objects to dispose.",
"<code>AsSplitQuery</code> fixes cartesian explosion but adds round trips — still better than millions of duplicate rows.",
"The global default for <code>AsSplitQuery</code> can be set in <code>OnConfiguring</code>; override per-query with <code>AsSingleQuery()</code>."],
f'''
<h3>1. Spotting N+1 with LogTo</h3>
<p>The pattern is easy to miss because each query looks innocent:</p>
{C(r"""
await using var db = Db.Create(logSql: true);   // LogTo is active

var customers = await db.Customers.ToListAsync();     // 1 query: SELECT * FROM Customers
foreach (var c in customers)
{
    // ❌ Each iteration fires: SELECT * FROM Orders WHERE CustomerId = @p
    Console.WriteLine($"{c.Name} has {c.Orders.Count} orders");
}
// With 50 customers → 1 + 50 = 51 queries. Console shows them all.
""", "N+1Demo.cs")}
{tip("Turn on <code>LogTo</code> during development. The right number of SQL statements for a list page is almost always 1 (or 2 with <code>AsSplitQuery</code>).")}
<h4>Fix: Include</h4>
{C(r"""
var customers = await db.Customers
    .Include(c => c.Orders)
    .ToListAsync();
// 1 query. EF joins Orders in and populates c.Orders from the result set.
""")}
<h4>Fix: projection (often better)</h4>
{C(r"""
var summaries = await db.Customers
    .Select(c => new {{ c.Name, c.City, OrderCount = c.Orders.Count }})
    .ToListAsync();
// 1 query:
// SELECT c.Name, c.City, (SELECT COUNT(*) FROM Orders WHERE CustomerId = c.Id) AS OrderCount
// FROM Customers AS c
// No navigation loaded at all.
""")}

<h3>2. AsNoTracking — faster read-only queries</h3>
{C(r"""
await using var db = Db.Create(logSql: false);

// ✓ No tracking: entities are not added to the ChangeTracker snapshot
var orders = await db.Orders
    .AsNoTracking()
    .Include(o => o.Customer)
    .Where(o => o.Status == OrderStatus.Paid)
    .ToListAsync();

// If two Orders share Customer id=1 and tracking is off, two DIFFERENT Customer objects
// are created (identity resolution is skipped).
Console.WriteLine(orders[0].Customer == orders[1].Customer);   // possibly False

// AsNoTrackingWithIdentityResolution: de-duplication without change tracking
var withId = await db.Orders
    .AsNoTrackingWithIdentityResolution()
    .Include(o => o.Customer)
    .Where(o => o.Status == OrderStatus.Paid)
    .ToListAsync();
// Now orders[0].Customer == orders[1].Customer if they share the same CustomerId ✓
""", "NoTracking.cs")}
{table(["","Default (tracking)","AsNoTracking","AsNoTrackingWithIdentityResolution"],[
["Change tracker snapshot","Yes","No","No"],
["SaveChanges picks up changes","Yes","No","No"],
["Identity resolution","Yes","No","Yes"],
["Memory","Highest","Lowest","Medium"],
["Use when","Mutations needed","Read-only list/report","Read-only but want shared objects"]])}

<h3>3. Projections to DTOs</h3>
<p>Project in the <code>Select</code> — the SQL goes to the database; no entities come back to track.</p>
{C(r"""
// A lightweight record for an order summary page
public record OrderSummaryDto(
    int OrderId,
    string CustomerName,
    string City,
    DateTime OrderDateUtc,
    decimal Total,
    int ItemCount);
""", "OrderSummaryDto.cs")}
{C(r"""
var summaries = await db.Orders
    .Where(o => o.Status != OrderStatus.Cancelled)
    .Select(o => new OrderSummaryDto(
        o.Id,
        o.Customer.Name,                                // EF translates the navigation
        o.Customer.City,
        o.OrderDateUtc,
        o.Lines.Sum(l => l.Quantity * l.UnitPrice),     // aggregate in the SELECT
        o.Lines.Count))
    .OrderByDescending(d => d.OrderDateUtc)
    .Take(20)
    .ToListAsync();
""", "OrderQueries.cs")}
{C(r"""
-- Generated SQL (illustrative):
SELECT TOP(20) [o].[Id],
    [c].[Name], [c].[City],
    [o].[OrderDateUtc],
    COALESCE((SELECT SUM([l].[Quantity] * [l].[UnitPrice]) FROM [OrderLines] AS [l]
              WHERE [o].[Id] = [l].[OrderId]), 0.0),
    (SELECT COUNT(*) FROM [OrderLines] AS [l] WHERE [o].[Id] = [l].[OrderId])
FROM [Orders] AS [o]
INNER JOIN [Customers] AS [c] ON [o].[CustomerId] = [c].[Id]
WHERE [o].[Status] <> 4
ORDER BY [o].[OrderDateUtc] DESC
""", "Generated SQL (example)", lang="sql")}
{tip("No entity, no tracking overhead, no risk of serialising lazy navigations. For list/report endpoints prefer projections over Include.")}

<h3>4. Cartesian explosion and AsSplitQuery</h3>
<p>When you Include two or more collections on the same entity, EF joins them all in one SELECT. The result set has one row for <b>every combination</b> of children:</p>
{C(r"""
// Suppose an Order has 5 Lines and 5 Tags.
// A single query returns 5 × 5 = 25 rows per order — the data is repeated 5× each.
// With 100 orders: 2,500 rows on the wire, most of them duplicates.
var orders = await db.Orders
    .Include(o => o.Lines).ThenInclude(l => l.Product)
    .Include(o => o.Tags)                              // second collection → explosion
    .ToListAsync();
""")}
<h4>Fix: AsSplitQuery</h4>
{C(r"""
var orders = await db.Orders
    .Include(o => o.Lines).ThenInclude(l => l.Product)
    .Include(o => o.Tags)
    .AsSplitQuery()          // EF runs: 1 SELECT for Orders+Lines+Products, 1 for Tags
    .ToListAsync();
// 2 round trips, but far fewer bytes and no duplicate data.

// Apply globally in OnConfiguring:
// builder.UseQuerySplittingBehavior(QuerySplittingBehavior.SplitQuery);
// Override back per query with:
// .AsSingleQuery()
""", "SplitQuery.cs")}
{table(["","Single query","Split query"],[
["Round trips","1","1 + (N collections included)"],
["Row duplication","Yes — cartesian product","No"],
["Consistency","Always a snapshot of one instant","Technically two transactions; a concurrent write can make them inconsistent"],
["Best when","Few or no collection Includes","Multiple collection Includes with large data"]])}
{warn("Use <code>AsSplitQuery</code> when you Include multiple collections and the data is large. Keep <code>AsSingleQuery</code> (the default) when you need a single consistent read across tables.", "Tradeoff")}

<h3>5. Combining tools: a customer dashboard query</h3>
{C(r"""
// A single-query projection: no tracking, no cartesian explosion, only needed columns
public record CustomerDashboardDto(
    int Id, string Name, string City,
    int TotalOrders, decimal LifetimeSpend, DateTime? LastOrderDate);

var dashboard = await db.Customers
    .AsNoTracking()
    .Select(c => new CustomerDashboardDto(
        c.Id, c.Name, c.City,
        c.Orders.Count,
        c.Orders.SelectMany(o => o.Lines).Sum(l => l.Quantity * l.UnitPrice),
        c.Orders.OrderByDescending(o => o.OrderDateUtc).Select(o => (DateTime?)o.OrderDateUtc).FirstOrDefault()))
    .OrderByDescending(d => d.LifetimeSpend)
    .ToListAsync();

foreach (var d in dashboard)
    Console.WriteLine($"{d.Name,-20} {d.City,-12} {d.TotalOrders,3} orders  ₹{{d.LifetimeSpend,10:N2}}");
// Asha Rao             Pune          5 orders  ₹12,450.00
// Ravi Kumar           Chennai       3 orders  ₹6,200.00
""")}
''',
["Calling <code>db.Customers.ToList()</code> then accessing <code>c.Orders</code> in a loop — the classic N+1.",
"Using Include for read-only list endpoints when a projection would be leaner.",
"Forgetting that AsNoTracking breaks identity resolution — two rows for the same customer create two objects.",
"Including multiple collections and hitting cartesian explosion without noticing (check row count in LogTo).",
"Setting AsSplitQuery globally and then needing one consistent snapshot — override with AsSingleQuery."],
("35 min", ["Enable <code>LogTo</code> and reproduce the N+1; then fix it three ways: Include, AsNoTracking + Include, and projection. Count SQL statements for each.",
"Write a projection DTO for the top 10 customers by lifetime spend (single query, no tracking, only needed columns).",
"Add a second collection (e.g. <code>Tags</code> as a simple list of strings on Order, or use <code>OrderLine</code> + products) and demonstrate cartesian explosion with LogTo, then fix with <code>AsSplitQuery</code>."]),
[("What is the N+1 problem in EF Core?","Loading a list of entities and then accessing a navigation property in a loop, causing one additional SELECT per row instead of a single JOIN."),
("When does AsNoTracking break identity resolution?","Always — by default it creates a new object for each row. Use AsNoTrackingWithIdentityResolution if you need a single C# object per database row but don't need change tracking."),
("When should you use AsSplitQuery?","When you Include two or more collections and the cross-product row count is large. The cost is an extra round trip and a small inconsistency window.")],
[("Basic","What is N+1 and how do you detect it in EF Core?","N+1 happens when a query returns N entities and then each entity causes one more database round trip (usually via a navigation property in a loop). Detect it by enabling <code>LogTo</code> and counting SQL statements, or by watching for repeated <code>SELECT ... WHERE ForeignKeyId = @p</code> patterns."),
("Basic","When should you use AsNoTracking?","For any query that is read-only: list pages, reports, API responses. It skips creating change-tracker snapshots — roughly 10–30% faster reads and significantly lower memory, especially with large result sets."),
("Intermediate","What is cartesian explosion and how does AsSplitQuery help?","When you Include two collections EF joins them in one SELECT; the result set rows equal the product of the collection sizes per parent. AsSplitQuery runs one SELECT per included collection instead, eliminating the duplicate data at the cost of an extra round trip."),
("Intermediate","Projection vs Include — when do you choose each?","Projection (Select to a DTO) generates a narrower SQL query with only the columns you name, requires no tracking, and avoids loading full entities. Include loads full entities with navigations. Use Include when the caller needs to mutate entities and call SaveChanges; use projection for read-only endpoints and reports."),
("Intermediate","What does AsNoTrackingWithIdentityResolution do?","It de-duplicates objects — the same row ID maps to one C# instance — without maintaining a change-tracker snapshot. Useful when multiple parents share the same child and you want reference equality without the memory cost of tracking."),
("Intermediate","How do you set AsSplitQuery globally?","In <code>OnConfiguring</code>: <code>options.UseQuerySplittingBehavior(QuerySplittingBehavior.SplitQuery)</code>. Per-query: append <code>.AsSplitQuery()</code>. Override back with <code>.AsSingleQuery()</code>.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Raw SQL: FromSql, SqlQuery, ExecuteUpdate/Delete, stored procedures, compiled queries",
"Drop below LINQ when you need control: parameterised raw SQL, bulk mutations without loading entities, stored procedures, and compiled queries for hot paths.",
[("FromSql","<code>db.Products.FromSql($\"...\")</code> — executes raw SQL that returns entity columns; maps the results to tracked entities. The <code>$</code> interpolated string is automatically parameterised."),
("FromSqlRaw","<code>db.Products.FromSqlRaw(\"...{0}\", value)</code> — raw SQL with explicit positional parameters. Use when the SQL is not a C# interpolated string."),
("SqlQuery","<code>db.Database.SqlQuery&lt;T&gt;()</code> (EF Core 7+) — returns arbitrary scalar/DTO types from raw SQL, not entity types."),
("ExecuteUpdate","<code>db.Products.Where(...).ExecuteUpdate(s =&gt; s.SetProperty(p =&gt; p.Stock, 0))</code> — bulk UPDATE without loading or tracking entities (EF Core 7+)."),
("ExecuteDelete","<code>db.Products.Where(...).ExecuteDelete()</code> — bulk DELETE without loading entities (EF Core 7+)."),
("Stored procedure","Pre-compiled SQL stored in the database, executed with <code>FromSql</code> or <code>Database.ExecuteSqlRaw</code>."),
("Output parameter","A SqlParameter with Direction = Output; used to get scalar values back from a stored proc."),
("Compiled query","<code>EF.CompileAsyncQuery(...)</code> — caches query translation so the LINQ→SQL translation step is skipped on every call. Only for very hot paths."),
("SQL injection","Inserting malicious SQL via user input. Never concatenate user strings into SQL; always parameterise."),
("FormattableString","C#'s type for interpolated strings: <code>$\"...{value}\"</code>. EF's <code>FromSql</code> accepts it and uses the holes as parameters, not string concatenation.")],
["<code>FromSql</code> with an interpolated string is safe — EF parameterises the holes. <code>FromSqlRaw</code> with string concatenation is not.",
"<code>FromSql</code> must SELECT all entity columns (or at least the ones mapped); you can compose further LINQ on top.",
"<code>ExecuteUpdate</code> / <code>ExecuteDelete</code> bypass the change tracker and do not trigger interceptors or SaveChanges.",
"Compiled queries pay off only on very high-frequency paths (thousands per second); measure first.",
"Stored procedures that return a result set map nicely to FromSql; those that don't return rows use <code>ExecuteSqlRaw</code>."],
f'''
<h3>1. FromSql — raw SELECT mapped to entities</h3>
{C(r"""
await using var db = Db.Create();

// ✓ Interpolated string — EF makes this @p0 automatically
string city = "Pune";
var puneCusts = await db.Customers
    .FromSql($"SELECT * FROM Customers WHERE City = {{city}}")   // {{ }} in f-string prose, plain {{}} inside C
    .OrderBy(c => c.Name)
    .ToListAsync();

// You can compose LINQ on top of FromSql
var puneWithOrders = await db.Customers
    .FromSql($"SELECT * FROM Customers WHERE City = {{city}}")
    .Include(c => c.Orders)                 // EF wraps the raw SQL in a subquery and JOINs
    .Where(c => c.Orders.Any())
    .ToListAsync();
""", "FromSqlDemo.cs")}
{warn("Never do <code>FromSqlRaw($\"SELECT * FROM Customers WHERE City = '{city}'\")</code> — that's string concatenation, not parameterisation, and it's wide open to SQL injection.", "Security")}
{C(r"""
// FromSqlRaw with explicit parameters — safe
var city2 = "Chennai";
var chCusts = await db.Customers
    .FromSqlRaw("SELECT * FROM Customers WHERE City = {0}", city2)
    .ToListAsync();

// Also accepts SqlParameter objects (useful for stored procs with named params)
using var param = new Microsoft.Data.SqlClient.SqlParameter("@city", city2);
var chCusts2 = await db.Customers
    .FromSqlRaw("SELECT * FROM Customers WHERE City = @city", param)
    .ToListAsync();
""")}

<h3>2. SqlQuery — arbitrary result types (EF Core 7+)</h3>
<p>When the query doesn't map to an entity — aggregates, custom projections, stored proc scalars:</p>
{C(r"""
// A simple DTO not in the DbContext
public record CitySalesDto(string City, int OrderCount, decimal Revenue);

var citySales = await db.Database
    .SqlQuery<CitySalesDto>($@"
        SELECT c.City,
               COUNT(DISTINCT o.Id) AS OrderCount,
               COALESCE(SUM(l.Quantity * l.UnitPrice), 0) AS Revenue
        FROM Customers c
        JOIN Orders o ON o.CustomerId = c.Id
        JOIN OrderLines l ON l.OrderId = o.Id
        WHERE o.Status = 2    -- Paid
        GROUP BY c.City
        ORDER BY Revenue DESC")
    .ToListAsync();

foreach (var r in citySales)
    Console.WriteLine($"{r.City,-12} {r.OrderCount,3} orders  ₹{r.Revenue:N2}");

// SqlQuery also works for scalars with KeylessEntity or a wrapper record:
var total = await db.Database.SqlQuery<decimal>($"SELECT CAST(SUM(UnitPrice * Quantity) AS decimal(18,2)) FROM OrderLines").FirstAsync();
Console.WriteLine($"Grand total: ₹{total:N2}");
""", "SqlQueryDemo.cs")}

<h3>3. ExecuteUpdate and ExecuteDelete (EF Core 7+)</h3>
<p>Bulk mutations that run one SQL statement on the server without loading entities first:</p>
{C(r"""
await using var db = Db.Create();

// Bulk UPDATE: raise all Grocery prices by 5%
int rows = await db.Products
    .Where(p => p.Category.Name == "Grocery")
    .ExecuteUpdateAsync(s => s
        .SetProperty(p => p.Price, p => p.Price * 1.05m)
        .SetProperty(p => p.Stock, p => p.Stock));          // unchanged column — often omitted; shown for clarity
Console.WriteLine($"Updated {rows} rows");

// Generated SQL:
// UPDATE [Products] SET [Price] = [Price] * 1.05
// FROM [Products] AS [p]
// INNER JOIN [Categories] AS [c] ON [p].[CategoryId] = [c].[Id]
// WHERE [c].[Name] = N'Grocery'

// Bulk DELETE: remove cancelled orders older than 1 year
var cutoff = DateTime.UtcNow.AddYears(-1);
int deleted = await db.Orders
    .Where(o => o.Status == OrderStatus.Cancelled && o.OrderDateUtc < cutoff)
    .ExecuteDeleteAsync();
Console.WriteLine($"Deleted {deleted} old cancelled orders");
""", "BulkMutations.cs")}
{warn("<code>ExecuteUpdate/Delete</code> bypass interceptors, navigation fix-up, and <code>SaveChanges</code>. If your context has tracked copies of the affected rows, they won't reflect the change — refresh or discard them.", "Gotcha")}

<h3>4. Stored procedures</h3>
{C(r"""
-- Create in SQL Server first
CREATE OR ALTER PROCEDURE usp_TopCustomers
    @MinSpend   decimal(18,2),
    @TopN       int
AS
    SELECT TOP (@TopN)
           c.Id, c.Name, c.Email, c.City,
           SUM(l.Quantity * l.UnitPrice) AS LifetimeSpend
    FROM Customers c
    JOIN Orders  o ON o.CustomerId = c.Id
    JOIN OrderLines l ON l.OrderId = o.Id
    GROUP BY c.Id, c.Name, c.Email, c.City
    HAVING SUM(l.Quantity * l.UnitPrice) >= @MinSpend
    ORDER BY LifetimeSpend DESC
""", "usp_TopCustomers.sql", lang="sql")}
{C(r"""
// A DTO to receive the proc's result set
public record TopCustomerDto(int Id, string Name, string Email, string City, decimal LifetimeSpend);

var top = await db.Database
    .SqlQuery<TopCustomerDto>($"EXEC usp_TopCustomers @MinSpend = {{5000m}}, @TopN = {{5}}")
    .ToListAsync();

// Alternative: execute with explicit SqlParameters (needed for OUTPUT params)
using var spendParam = new Microsoft.Data.SqlClient.SqlParameter("@MinSpend", 5000m);
using var topNParam  = new Microsoft.Data.SqlClient.SqlParameter("@TopN", 5);
var top2 = await db.Database
    .SqlQueryRaw<TopCustomerDto>("EXEC usp_TopCustomers @MinSpend, @TopN", spendParam, topNParam)
    .ToListAsync();

// ExecuteSqlRaw for a proc that doesn't return rows (e.g. archive job)
await db.Database.ExecuteSqlRawAsync("EXEC usp_ArchiveOldOrders @CutoffDate",
    new Microsoft.Data.SqlClient.SqlParameter("@CutoffDate", DateTime.UtcNow.AddYears(-1)));
""", "StoredProcDemo.cs")}

<h3>5. Compiled queries (EF Core 2+)</h3>
<p>LINQ-to-SQL translation is cached, but it still takes CPU on each call. For extremely hot paths compile the query once at startup:</p>
{C(r"""
// Declare at app startup or in a static class
private static readonly Func<StoreDbContext, int, Task<Customer?>> _getCustomerById =
    EF.CompileAsyncQuery((StoreDbContext db, int id) =>
        db.Customers
          .AsNoTracking()
          .Include(c => c.Orders)
          .SingleOrDefault(c => c.Id == id));

// Use anywhere — the LINQ→SQL translation step is skipped completely
Customer? c = await _getCustomerById(db, 42);

// Compiled queries have restrictions: no dynamic LINQ, no optional includes.
// All parameters must be primitive values captured by the lambda (no IEnumerable args).
""", "CompiledQuery.cs")}
{table(["","Regular LINQ query","Compiled query"],[
["First call","Translate LINQ → SQL, cache, execute","Translate LINQ → SQL, cache, execute"],
["Subsequent calls","Retrieve from cache, execute","Execute — translation step fully skipped"],
["Benefit","Near-zero in most apps","~5–15% faster on very high-frequency queries"],
["Restrictions","None","No dynamic expressions; parameters must be primitives"]])}
{tip("Profile before introducing compiled queries. For most apps <code>AsNoTracking</code> + projections give 90% of the gains with none of the complexity.")}
''',
["Using <code>FromSqlRaw</code> with string interpolation instead of <code>FromSql</code> with an interpolated FormattableString.",
"Forgetting that <code>ExecuteUpdate/Delete</code> doesn't sync tracked entities — stale data in the context.",
"Calling <code>FromSql</code> with a SELECT that doesn't return all entity columns (EF throws at materialisation time).",
"Using <code>SqlQuery&lt;T&gt;</code> with a type EF can't construct (needs a parameterless constructor or positional record)."],
("35 min", ["Execute a parameterised <code>FromSql</code> to list products by category name, then compose a LINQ <code>Where</code> and <code>OrderBy</code> on top.",
"Write an <code>ExecuteUpdate</code> to apply a 10% discount on all products with stock &gt; 100, then verify with a <code>SqlQuery&lt;T&gt;</code> to retrieve the totals.",
"Create stored proc <code>usp_MonthlyRevenue(@Year int, @Month int)</code> returning total revenue; call it from EF and print the result."]),
[("What is the difference between FromSql and FromSqlRaw?","<code>FromSql</code> takes an interpolated string (<code>FormattableString</code>) and automatically converts the holes to parameters — safe against injection. <code>FromSqlRaw</code> takes a plain string with <code>{0}</code> placeholders or named SqlParameters — also safe as long as you don't concatenate user input into the string."),
("Can you use LINQ after FromSql?","Yes. EF wraps the raw SQL in a subquery (<code>SELECT ... FROM (...) AS [t]</code>) and applies your LINQ predicates on top. The combined query executes as one round trip."),
("When would you use ExecuteDelete instead of removing entities and calling SaveChanges?","When you need to delete many rows at once without loading them: bulk deletes of old records, cleanup jobs, etc. It runs a single SQL DELETE on the server and is far faster than load → track → delete → save per entity.")],
[("Basic","Why must you parameterise raw SQL queries?","To prevent SQL injection — an attacker can terminate your SQL and append malicious statements. EF's FromSql interpolation and FromSqlRaw with placeholders both send values as parameters; the SQL engine treats them as data, not code."),
("Basic","What does ExecuteUpdate do differently from updating tracked entities?","It issues a single bulk UPDATE directly on the database server without loading any entities. No change-tracker snapshots, no interceptors, and no calls to SaveChanges — faster and lower memory, but tracked copies in the same context won't reflect the change."),
("Intermediate","When would you choose SqlQuery over FromSql?","When the result doesn't map to an entity type registered in the DbContext: aggregate results, stored procedure outputs that mix columns, or completely custom projections. SqlQuery materialises into any class or record EF can construct."),
("Intermediate","What restrictions apply to EF compiled queries?","All query parameters must be primitives (int, string, bool, etc.) captured by the lambda. No dynamic LINQ building, no IQueryable arguments, no optional navigation includes. The benefit is skipping LINQ-to-SQL translation on every call; it's only measurable on very hot paths (thousands of calls per second)."),
("Intermediate","How do you call a stored procedure that returns no rows?","<code>db.Database.ExecuteSqlRaw(\"EXEC ...\", params)</code> or <code>ExecuteSqlRawAsync</code>. For scalar OUTPUT parameters, pass a <code>SqlParameter</code> with Direction set to Output and read its Value after the call."),
("Advanced","What is the risk of using ExecuteUpdate/Delete with interceptors?","ExecuteUpdate/Delete bypass SaveInterceptors and SaveChanges hooks entirely. If you have audit logging, soft-delete logic, or domain events wired into SaveChangesAsync, they won't fire. Use them only when you're sure no interceptor work is needed, or add your own logic explicitly.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Optimistic concurrency, transactions and execution strategies",
"Handle concurrent edits with rowversion, recover from DbUpdateConcurrencyException, and manage transactions — including how execution strategies interact with explicit transactions.",
[("Optimistic concurrency","Assumes conflicts are rare: let two users read the same row, but detect and reject a second save if the first already changed it."),
("rowversion","A SQL Server 8-byte binary column (<code>ROWVERSION</code> / <code>TIMESTAMP</code>) auto-incremented by the engine on every UPDATE. EF Core maps it with <code>[Timestamp]</code>."),
("ConcurrencyToken","Any column marked <code>[ConcurrencyCheck]</code> or via Fluent API <code>IsConcurrencyToken()</code>; EF adds its current value to the WHERE clause of every UPDATE/DELETE."),
("DbUpdateConcurrencyException","Thrown when no row was affected by an UPDATE/DELETE because another writer changed the row first. Its <code>Entries</code> property gives the conflicting entities."),
("Reload strategy","Discard your changes and reload from the database — \"last writer wins, but you're the loser\".",),
("Client-wins strategy","Keep your proposed values and overwrite the database — use only when you're certain this is correct."),
("Merge strategy","Read the current DB values and re-apply your changes where there's no overlap — most sophisticated."),
("Implicit transaction","Every <code>SaveChanges</code> call runs inside its own transaction automatically."),
("BeginTransaction","<code>db.Database.BeginTransactionAsync()</code> opens an explicit transaction for multiple SaveChanges calls."),
("Execution strategy","A retry policy (<code>EnableRetryOnFailure</code>) that re-runs the whole operation on transient errors — connection drops, SQL Server restart, Azure SQL throttling."),
("Idempotent operation","An operation that can run multiple times and produce the same result — required when execution strategies retry.")],
["Every UPDATE/DELETE with a rowversion adds <code>WHERE RowVersion = @orig</code>; 0 rows affected = exception.",
"<code>Entries[0].GetDatabaseValues()</code> costs one extra round trip — do it only when you need to merge.",
"Always catch <code>DbUpdateConcurrencyException</code> in a retry loop, not just once; two users may both fail and retry.",
"Implicit transactions wrap a single SaveChanges; for \"all or nothing\" across two SaveChanges calls, use an explicit transaction.",
"You can't use <code>db.Database.BeginTransaction()</code> inside an execution strategy — wrap the whole retry in <code>strategy.ExecuteAsync</code>."],
f'''
<h3>1. Add rowversion to Order</h3>
{C(r"""
public class Order
{{
    public int Id {{ get; set; }}
    public int CustomerId {{ get; set; }}
    public Customer Customer {{ get; set; }} = null!;
    public DateTime OrderDateUtc {{ get; set; }}
    public OrderStatus Status {{ get; set; }}
    public List<OrderLine> Lines {{ get; set; }} = [];

    // Auto-incremented by SQL Server on every UPDATE
    [System.ComponentModel.DataAnnotations.Timestamp]
    public byte[] RowVersion {{ get; set; }} = [];
}}
""", "Order.cs (rowversion added)")}
{C(r"""
// Or via Fluent API in OrderConfiguration:
b.Property(o => o.RowVersion)
 .IsRowVersion()          // equivalent to [Timestamp] — maps to ROWVERSION column
 .IsConcurrencyToken();   // implied by IsRowVersion(), but explicit makes the intent clear
""", "OrderConfiguration.cs (fragment)")}
{C(r"""
dotnet ef migrations add AddRowVersionToOrder -p Store.Data -s Store.App
dotnet ef database update -p Store.Data -s Store.App
""", lang="bash")}

<h3>2. Detecting and handling the conflict</h3>
{C(r"""
// Two users both load order 1 at the same time
await using var db1 = Db.Create(logSql: false);
await using var db2 = Db.Create(logSql: false);

var order1 = await db1.Orders.SingleAsync(o => o.Id == 1);
var order2 = await db2.Orders.SingleAsync(o => o.Id == 1);

// User 1 ships the order and saves
order1.Status = OrderStatus.Shipped;
await db1.SaveChangesAsync();      // succeeds; RowVersion bumped by SQL Server

// User 2 (db2) now tries to cancel — but the row changed
order2.Status = OrderStatus.Cancelled;
try
{
    await db2.SaveChangesAsync();   // ❌ DbUpdateConcurrencyException: 0 rows affected
}
catch (DbUpdateConcurrencyException ex)
{
    var entry = ex.Entries.Single();
    var dbValues = await entry.GetDatabaseValuesAsync();   // 1 extra round trip
    if (dbValues is null)
    {
        Console.WriteLine("Order was deleted by another user.");
        return;
    }

    var dbStatus = (OrderStatus)dbValues[nameof(Order.Status)]!;
    Console.WriteLine($"Conflict: DB has Status={dbStatus}, you wanted Cancelled");

    // ---- Strategy 1: Reload (discard local changes) ----
    // entry.OriginalValues.SetValues(dbValues);   // update original so EF no longer sees a conflict
    // entry.CurrentValues.SetValues(dbValues);    // discard local changes

    // ---- Strategy 2: Client wins (force your values over the DB) ----
    // entry.OriginalValues.SetValues(dbValues);   // update rowversion so the next save succeeds

    // ---- Strategy 3: Merge (combine non-conflicting fields) ----
    var currentValues = entry.CurrentValues;
    foreach (var prop in dbValues.Properties)
    {{
        var dbVal     = dbValues[prop];
        var clientVal = currentValues[prop];
        var origVal   = entry.OriginalValues[prop];
        // Keep client value only if neither we nor the other writer changed it
        currentValues[prop] = Equals(clientVal, origVal) ? dbVal : clientVal;
    }}
    entry.OriginalValues.SetValues(dbValues);   // accept new rowversion

    await db2.SaveChangesAsync();               // retry
}
""", "ConcurrencyDemo.cs")}

<h3>3. Transactions — implicit and explicit</h3>
<p>Every <code>SaveChanges</code> is automatically wrapped in a transaction. Use explicit transactions when you need atomicity across two calls or want to mix EF with raw SQL:</p>
{C(r"""
await using var db = Db.Create();
await using var tx = await db.Database.BeginTransactionAsync();
try
{{
    // All work inside the same context and transaction
    var order = await db.Orders.Include(o => o.Lines).SingleAsync(o => o.Id == 2);

    // 1) Update order status
    order.Status = OrderStatus.Shipped;
    await db.SaveChangesAsync();         // still inside the tx, not committed

    // 2) Insert a shipping audit record (raw SQL)
    await db.Database.ExecuteSqlRawAsync(
        "INSERT INTO ShippingAudit (OrderId, ShippedUtc, ShippedBy) VALUES ({0}, GETUTCDATE(), {1})",
        order.Id, "SystemJob");

    await tx.CommitAsync();              // commit both changes together
    Console.WriteLine("Order shipped and audit record written.");
}}
catch
{{
    await tx.RollbackAsync();
    throw;
}}
""", "ExplicitTransaction.cs")}

<h3>4. Execution strategies and EnableRetryOnFailure</h3>
<p>Cloud databases (Azure SQL, SQL Server in Docker) return transient errors. Configure a retry policy:</p>
{C(r"""
var builder = new DbContextOptionsBuilder<StoreDbContext>()
    .UseSqlServer(Db.ConnectionString, opts =>
        opts.EnableRetryOnFailure(
            maxRetryCount: 5,
            maxRetryDelay: TimeSpan.FromSeconds(30),
            errorNumbersToAdd: null));       // null = use EF's default transient error list

// The strategy handles: connection drops, deadlocks (1205), login throttle (18056), etc.
""", "RetrySetup.cs (fragment)")}
{warn("<code>BeginTransaction</code> is <b>incompatible</b> with execution strategies — the strategy can't retry if it doesn't control the transaction boundary. Solution: wrap the whole unit of work in <code>strategy.ExecuteAsync</code>:", "Gotcha")}
{C(r"""
var strategy = db.Database.CreateExecutionStrategy();

await strategy.ExecuteAsync(async () =>
{{
    await using var tx = await db.Database.BeginTransactionAsync();
    try
    {{
        // ... all work here, same as above ...
        await tx.CommitAsync();
    }}
    catch
    {{
        await tx.RollbackAsync();
        throw;
    }}
}});
// The strategy wraps the entire lambda. If a transient error occurs, the whole lambda
// (including the transaction) reruns from the top → must be idempotent.
""", "StrategyWithTransaction.cs")}
{table(["Scenario","Approach"],[
["Single SaveChanges, no retries needed","Let EF use the implicit transaction"],
["Multiple SaveChanges that must all succeed or fail","<code>BeginTransaction / Commit / Rollback</code>"],
["Cloud database with transient faults, single SaveChanges","<code>EnableRetryOnFailure</code> in <code>UseSqlServer</code>"],
["Cloud database + explicit transaction","<code>strategy.ExecuteAsync(async () =&gt; {{ ... tx ... }})</code>"]])}
''',
["Adding <code>[Timestamp]</code> but forgetting to migrate — the column doesn't exist and all concurrency checks are skipped.",
"Catching the exception once; a second concurrent conflict will re-throw and bubble up uncaught.",
"Using <code>db.Database.BeginTransaction()</code> without wrapping in <code>strategy.ExecuteAsync</code> when retries are on.",
"Calling <code>GetDatabaseValues()</code> inside a tight retry loop — it adds a round trip each time.",
"Assuming the implicit transaction covers two separate <code>SaveChanges</code> calls — it doesn't."],
("35 min", ["Add a <code>[Timestamp] RowVersion</code> to Order, migrate, then write a demo where two contexts update the same order and handle the conflict with the merge strategy.",
"Write an explicit transaction that ships an order AND inserts a shipping log row (raw SQL); verify both are rolled back if the second step throws.",
"Configure <code>EnableRetryOnFailure(5, 30s)</code>; simulate a transient error by temporarily renaming the database, observe EF retrying, then rename it back."]),
[("What column type does [Timestamp] map to in SQL Server?","ROWVERSION (historically called TIMESTAMP). It's an 8-byte binary value incremented by the engine on every row update — not a date/time column."),
("Why can't you use BeginTransaction inside an execution strategy?","An execution strategy replays the entire operation lambda on a transient error. If you open a transaction outside its control, the strategy can't roll it back and retry cleanly — EF throws an InvalidOperationException telling you to wrap the tx in strategy.ExecuteAsync."),
("How does EF Core use the rowversion in a WHERE clause?","Every UPDATE and DELETE adds <code>WHERE RowVersion = @originalValue</code>. If another writer already updated the row, its rowversion changed, 0 rows are affected, and EF throws DbUpdateConcurrencyException.")],
[("Basic","What is optimistic concurrency and how does EF Core implement it?","Optimistic concurrency assumes conflicts are rare. EF Core adds the original value of a concurrency token (e.g. RowVersion) to the WHERE clause of UPDATE/DELETE. If another writer already changed the row, the WHERE matches 0 rows and EF throws DbUpdateConcurrencyException."),
("Basic","What is the difference between an implicit and an explicit transaction in EF Core?","Implicit: every SaveChanges call is automatically wrapped in one transaction; if anything fails, all changes in that call roll back. Explicit: you call BeginTransaction and Commit yourself, so multiple SaveChanges calls or mixed EF + raw SQL can be part of the same atomic unit."),
("Intermediate","Describe the three strategies for handling DbUpdateConcurrencyException.","Reload (discard local changes): copy database values to both OriginalValues and CurrentValues — lose your edits. Client wins (force write): copy database values to OriginalValues only — your edits overwrite whatever the other writer did. Merge: compare each property; keep the client value only where the client actually changed it, otherwise take the database value. Then retry SaveChanges."),
("Intermediate","What is EnableRetryOnFailure and what errors does it handle?","A SQL Server-specific execution strategy that re-runs the operation lambda on transient errors — network drops, login throttling, deadlocks. It retries up to <code>maxRetryCount</code> times with exponential back-off."),
("Intermediate","What must an operation wrapped in an execution strategy be?","Idempotent — running it multiple times must produce the same result. If the strategy retries after a transient failure, the entire lambda reruns including any side effects (emails sent, messages published). Factor those side effects out or use an outbox pattern."),
("Advanced","How would you implement an \"audit log\" that records every concurrent conflict?","Catch DbUpdateConcurrencyException, log the entry's EntityType, the original values and the database values, then decide the resolution strategy (reload/merge/client-wins) and retry. For a durable audit: write the conflict record to an AuditConflict table inside the same transaction as the retry, so either both succeed or neither does.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Owned types, value conversions, global query filters, shadow properties, HasData seeding",
"Model fine-grained domain concepts without extra tables, store non-primitive values in the database, filter stale rows automatically, and seed reference data cleanly.",
[("Owned type","An entity whose identity is defined by its owner. It maps to the same table by default (<code>OwnsOne/OwnsMany</code>). It has no <code>DbSet</code> of its own."),
("OwnsOne","Maps one owned object into columns in the owner's table: <code>b.OwnsOne(c =&gt; c.Address)</code>."),
("OwnsMany","Maps a collection of owned objects to a separate table linked by the owner's key."),
("Value conversion","A pair of functions that translate a CLR type to a column type and back: e.g. <code>enum</code> → <code>nvarchar</code>."),
("ValueConverter&lt;TModel, TProvider&gt;","The base class. EF has built-in converters for common patterns; pass a lambda to <code>HasConversion</code> for custom ones."),
("Global query filter","A <code>Where</code> applied automatically to every query on a type: <code>modelBuilder.Entity&lt;T&gt;().HasQueryFilter(x =&gt; !x.IsDeleted)</code>."),
("IgnoreQueryFilters","Appending <code>.IgnoreQueryFilters()</code> to a query bypasses all global filters for that query."),
("Shadow property","A property that exists in the EF model and the database column but not in the C# class. Accessed via <code>EF.Property&lt;T&gt;(entity, \"Name\")</code>."),
("HasData","Seeds constant reference data inside a migration; <code>HasData</code> entities must have all required properties and no navigations set."),
("Custom seeding","Running data inserts in a startup method (e.g. <code>dbContext.Database.MigrateAsync</code> then checking <code>Any()</code>); works for data that changes or depends on runtime state.")],
["Owned types are great for Address, Money, GeoPoint — value objects that shouldn't have their own table.",
"Value conversions run <i>in memory</i> after EF retrieves the data — LINQ operators that use the converted type may not translate to SQL. Keep conversions simple.",
"Global query filters apply to navigations loaded with Include too — no extra code needed.",
"Shadow properties are useful for audit columns (<code>CreatedBy</code>, <code>UpdatedAt</code>) you don't want on every entity class.",
"HasData requires you to supply PK values explicitly and doesn't support navigation properties."],
f'''
<h3>1. Owned types — value objects without extra tables</h3>
{C(r"""
// Address is a value object: no Id, no DbSet, lives inside Customer's table
public class Address
{{
    public string Street  {{ get; set; }} = "";
    public string City    {{ get; set; }} = "";
    public string State   {{ get; set; }} = "";
    public string PinCode {{ get; set; }} = "";  // e.g. "411001" Pune, "400001" Mumbai
}}

public class Customer
{{
    public int Id {{ get; set; }}
    public required string Name  {{ get; set; }}
    public required string Email {{ get; set; }}
    public Address ShippingAddress {{ get; set; }} = new();
    public List<Order> Orders {{ get; set; }} = [];
}}
""", "Customer.cs (owned type)")}
{C(r"""
// In CustomerConfiguration:
b.OwnsOne(c => c.ShippingAddress, a =>
{{
    a.Property(x => x.Street).HasMaxLength(200).HasColumnName("ShipStreet");
    a.Property(x => x.City).HasMaxLength(60).HasColumnName("ShipCity");
    a.Property(x => x.State).HasMaxLength(60).HasColumnName("ShipState");
    a.Property(x => x.PinCode).HasMaxLength(10).HasColumnName("ShipPinCode")
     .IsRequired(false);                // allow customers without an address yet
}});
// Columns are added to the Customers table — no join needed.
""", "CustomerConfiguration.cs (fragment)")}
{C(r"""
// Creating and querying
var cust = new Customer
{{
    Name = "Meena Iyer", Email = "meena@example.in",
    ShippingAddress = new Address {{ City = "Bengaluru", PinCode = "560001", State = "Karnataka", Street = "MG Road" }}
}};
db.Customers.Add(cust);
await db.SaveChangesAsync();

var c = await db.Customers.FirstAsync(x => x.ShippingAddress.City == "Bengaluru");
Console.WriteLine(c.ShippingAddress.PinCode);   // 560001
""")}
<h4>OwnsMany — collection of owned objects</h4>
{C(r"""
// A list of phone numbers owned by Customer, stored in a separate table
public class PhoneNumber
{{
    public string Type   {{ get; set; }} = "Mobile";   // "Mobile", "Work"
    public string Number {{ get; set; }} = "";
}}

public class Customer
{{
    // ...
    public List<PhoneNumber> PhoneNumbers {{ get; set; }} = [];
}}

// In configuration:
b.OwnsMany(c => c.PhoneNumbers, p =>
{{
    p.ToTable("CustomerPhones");
    p.Property(x => x.Number).HasMaxLength(20);
}});
""")}

<h3>2. Value conversions</h3>
<p>Store enums as strings (readable migrations, tolerant of reordering), or store a custom type like Money as a column:</p>
{C(r"""
// In OrderConfiguration — store Status as a readable string, not an int
b.Property(o => o.Status)
 .HasConversion<string>()           // built-in: enum → its Name string
 .HasMaxLength(20);
// Column: "Pending", "Paid", "Shipped", etc. instead of 0, 1, 2 …

// Custom converter: a Money value object → decimal column
public record Money(decimal Amount, string Currency = "INR")
{{
    public override string ToString() => $"₹{{Amount:N2}}";
}}

// In a hypothetical InvoiceConfiguration:
b.Property(i => i.TotalAmount)
 .HasConversion(
     m => m.Amount,                   // TModel → TProvider (C# → DB column)
     v => new Money(v));              // TProvider → TModel (DB column → C#)
""", "ValueConversions.cs (fragment)")}
{warn("Value conversions happen in memory. If you filter with <code>.Where(o =&gt; o.Status == OrderStatus.Paid)</code> and Status is stored as a string, EF Core 8 handles the round-trip correctly — but complex custom converters may prevent translation. Test with <code>ToQueryString()</code>.", "Gotcha")}

<h3>3. Global query filters</h3>
<p>Add a <code>IsActive</code> flag to Category, then never forget to filter it:</p>
{C(r"""
public class Category
{{
    public int Id {{ get; set; }}
    public required string Name {{ get; set; }}
    public bool IsActive {{ get; set; }} = true;
    public List<Product> Products {{ get; set; }} = [];
}}

// In StoreDbContext.OnModelCreating or CategoryConfiguration:
modelBuilder.Entity<Category>().HasQueryFilter(c => c.IsActive);
// Now: db.Categories.ToList() generates WHERE IsActive = 1 automatically.
// Even: db.Products.Include(p => p.Category).ToList() — inactive categories are excluded.
""", "GlobalFilter.cs (fragment)")}
{C(r"""
// Bypass for admin screens or seeding checks
var all = await db.Categories.IgnoreQueryFilters().ToListAsync();
Console.WriteLine(all.Count);           // includes inactive categories
""", "IgnoreFilters.cs (fragment)")}
{tip("Global filters apply to navigations loaded with Include. If you Include a navigation whose entity has a filter, only matching children appear — the parent still loads.")}

<h3>4. Shadow properties — audit columns without cluttering the entity</h3>
{C(r"""
// In StoreDbContext.OnModelCreating, add shadow properties to every entity:
foreach (var entityType in modelBuilder.Model.GetEntityTypes()
             .Where(e => !e.IsOwned()))
{{
    modelBuilder.Entity(entityType.Name).Property<DateTime>("CreatedAt");
    modelBuilder.Entity(entityType.Name).Property<DateTime>("UpdatedAt");
    modelBuilder.Entity(entityType.Name).Property<string?>("CreatedBy").HasMaxLength(100);
}}

// Set them in a SaveChanges override:
public override int SaveChanges()
{{
    var now = DateTime.UtcNow;
    foreach (var entry in ChangeTracker.Entries()
                 .Where(e => e.State is EntityState.Added or EntityState.Modified))
    {{
        entry.Property("UpdatedAt").CurrentValue = now;
        if (entry.State == EntityState.Added)
            entry.Property("CreatedAt").CurrentValue = now;
    }}
    return base.SaveChanges();
}}

// Querying a shadow property:
var recentOrders = await db.Orders
    .Where(o => EF.Property<DateTime>(o, "CreatedAt") >= DateTime.UtcNow.AddDays(-7))
    .ToListAsync();
""", "ShadowProperties.cs (fragment)")}

<h3>5. HasData vs custom seeding</h3>
{C(r"""
// HasData — good for reference data (categories, states, roles) that ships with the app
protected override void OnModelCreating(ModelBuilder modelBuilder)
{{
    modelBuilder.ApplyConfigurationsFromAssembly(typeof(StoreDbContext).Assembly);

    modelBuilder.Entity<Category>().HasData(
        new Category {{ Id = 1, Name = "Grocery",     IsActive = true }},
        new Category {{ Id = 2, Name = "Electronics", IsActive = true }},
        new Category {{ Id = 3, Name = "Home",        IsActive = true }},
        new Category {{ Id = 4, Name = "Clothing",    IsActive = true }}
    );
}}
// A new migration adds INSERT INTO statements for these rows.
// If you change them, the next migration adds UPDATE or DELETE accordingly.
""", "HasData.cs (fragment)")}
{C(r"""
// Custom seeding — for data that changes, is large, or depends on runtime configuration
public static async Task SeedDemoDataAsync(StoreDbContext db)
{{
    if (await db.Customers.AnyAsync()) return;   // idempotent: skip if already seeded

    db.Customers.AddRange(
        new Customer {{ Name = "Asha Rao",    Email = "asha@example.in",  ShippingAddress = new Address {{ City = "Pune" }} }},
        new Customer {{ Name = "Ravi Kumar",  Email = "ravi@example.in",  ShippingAddress = new Address {{ City = "Chennai" }} }},
        new Customer {{ Name = "Meena Iyer",  Email = "meena@example.in", ShippingAddress = new Address {{ City = "Bengaluru" }} }}
    );
    await db.SaveChangesAsync();
}}

// Call at startup, after MigrateAsync:
// await db.Database.MigrateAsync();
// await SeedDemoDataAsync(db);
""", "CustomSeed.cs")}
{table(["","HasData","Custom seeding"],[
["Lives in","Migration (SQL INSERTs)","Application startup code"],
["Good for","Stable reference data","Dynamic or large data sets"],
["Requires explicit PK","Yes","No"],
["Supports navigation properties","No","Yes"],
["Idempotent","Yes (migration tracks it)","Must implement yourself (e.g. Any() check)"]])}
''',
["Trying to query through an owned type's navigation with standard LINQ — owned types are queried through their owner.",
"Applying a value conversion for a type EF can't translate in a Where clause — test with ToQueryString() first.",
"Forgetting IgnoreQueryFilters in an admin or seeding context, causing incomplete data.",
"Supplying a navigation property in HasData — EF throws at migration generation time.",
"Shadow property names with typos (they're strings) silently default or throw at runtime."],
("35 min", ["Add an owned <code>Address</code> type to Customer, migrate, seed three customers with Indian addresses, and query by PinCode.",
"Apply a global query filter for <code>IsActive</code> on Product (new column, default true). Write queries that use it and bypass it with <code>IgnoreQueryFilters</code>.",
"Add <code>CreatedAt</code> and <code>UpdatedAt</code> shadow properties to Order via a <code>SaveChanges</code> override and confirm they're set by querying with <code>EF.Property&lt;DateTime&gt;</code>."]),
[("What is an owned type and when would you use it?","An entity whose identity depends on its owner — it has no DbSet, no primary key of its own, and maps to the owner's table (OwnsOne) or a dependent table (OwnsMany). Use it for value objects: Address, Money, GeoCoordinate."),
("What does IgnoreQueryFilters do?","It tells EF to skip all global HasQueryFilter predicates for that specific query — useful for admin screens, includes of soft-deleted children, or seeding checks."),
("Why can't you set navigation properties in HasData?","HasData works at the migration level where EF serialises property values into SQL INSERTs. Navigation properties are EF runtime concepts, not column values, so they can't be represented.")],
[("Basic","What is a global query filter and how is it applied to Include?","A predicate added with HasQueryFilter that EF appends automatically to every query on that entity type. When a filtered type is loaded via Include, the filter applies to the children too — only children matching the filter are included."),
("Basic","Owned type vs a separate entity — when would you choose each?","Owned type: no independent identity, always accessed through the owner, conceptually part of the owner (Address, Money). Separate entity: has its own identity and can be queried, shared between owners, or deleted independently."),
("Intermediate","How do shadow properties work and what are they useful for?","Shadow properties exist in the EF model and map to a database column, but have no corresponding C# property on the class. Useful for cross-cutting columns (CreatedAt, UpdatedAt, TenantId, IsDeleted) that you don't want on every entity class. Set them in a SaveChanges override and query them with EF.Property&lt;T&gt;."),
("Intermediate","What are the limitations of value conversions?","Conversions run in memory, not in the database. If EF can't translate a LINQ expression that uses the unconverted type, the query falls back to client-side evaluation or throws. Keep converters simple; test complex ones with ToQueryString() to verify they translate correctly."),
("Intermediate","HasData vs custom seeding — when is each appropriate?","HasData is best for stable reference data (categories, roles, country codes) that ships with the app and changes rarely; it's tracked in migrations, so changes generate UPDATE/DELETE SQL. Custom seeding is better for large data sets, data with relationships, or anything that changes between environments — seed it at startup with an idempotent check."),
("Intermediate","How does the enum-to-string value conversion affect migrations?","The column type changes from int to nvarchar(N). Migration 'down' scripts need to handle the reverse. With enum-to-string the column is human-readable and survives reordering of enum members; with int storage, inserting a new member before existing ones breaks all existing rows.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Soft delete + audit fields: ISoftDeletable, IAuditable, SaveChangesInterceptor",
"Build a production-ready cross-cutting concern: entities that are never hard-deleted, automatically timestamped, and always filtered — all wired through a single SaveChangesInterceptor.",
[("ISoftDeletable","An interface marking entities that must not be physically deleted: <code>bool IsDeleted</code> + <code>DateTime? DeletedAt</code>."),
("IAuditable","An interface for timestamp/author fields: <code>DateTime CreatedAt</code>, <code>DateTime UpdatedAt</code>, <code>string CreatedBy</code>, <code>string? UpdatedBy</code>."),
("SaveChangesInterceptor","An EF Core hook whose <code>SavingChanges</code> / <code>SavingChangesAsync</code> method runs just before every SaveChanges, letting you mutate entries."),
("IDbCommandInterceptor","Intercepts individual SQL commands — useful for logging, hinting or rewriting SQL."),
("SoftDeleteInterceptor","A SaveChangesInterceptor that turns any <code>EntityState.Deleted</code> entry for an ISoftDeletable into an Update that sets <code>IsDeleted = true</code>."),
("AuditInterceptor","A SaveChangesInterceptor that stamps <code>CreatedAt/UpdatedAt/CreatedBy/UpdatedBy</code> on Added/Modified entries."),
("ICurrentUserService","A service that returns the logged-in user's name or id — injected into the interceptor."),
("IgnoreQueryFilters","Used for admin restore screens to query soft-deleted rows."),
("dbContext.Entry(e).State","The EntityState: Detached, Unchanged, Added, Modified, Deleted.")],
["<code>SaveChangesInterceptor</code> runs inside the implicit transaction — if SaveChanges fails, the interceptor changes roll back too.",
"Change <code>EntityState.Deleted</code> to <code>EntityState.Modified</code> inside the interceptor so EF issues UPDATE, not DELETE.",
"The global query filter for <code>IsDeleted</code> must be applied to every soft-deletable entity — iterate <code>modelBuilder.Model.GetEntityTypes()</code>.",
"Test the interceptor with IgnoreQueryFilters to confirm soft-deleted rows exist in the database.",
"Keep interceptors focused: one for soft delete, one for audit. Chaining two separate interceptors is cleaner than one big one."],
f'''
<h3>Scaffold</h3>
{C(r"""
mkdir SoftDeleteAuditDemo && cd SoftDeleteAuditDemo
dotnet new sln
dotnet new classlib -n Core
dotnet new classlib -n Data
dotnet new console -n App
dotnet sln add Core Data App
dotnet add Data reference Core
dotnet add App reference Data
cd Data
dotnet add package Microsoft.EntityFrameworkCore.SqlServer
dotnet add package Microsoft.EntityFrameworkCore.Tools
cd ..
""", lang="bash")}

<h3>Step 1 — Interfaces</h3>
{C(r"""
namespace Core.Interfaces;

public interface ISoftDeletable
{{
    bool IsDeleted {{ get; set; }}
    DateTime? DeletedAt {{ get; set; }}
    string? DeletedBy {{ get; set; }}
}}

public interface IAuditable
{{
    DateTime CreatedAt  {{ get; set; }}
    DateTime UpdatedAt  {{ get; set; }}
    string   CreatedBy  {{ get; set; }}
    string?  UpdatedBy  {{ get; set; }}
}}

// Optional: convenience service to get the current user
public interface ICurrentUserService
{{
    string UserName {{ get; }}
}}
""", "Core/Interfaces/Interfaces.cs")}

<h3>Step 2 — Entities</h3>
{C(r"""
using Core.Interfaces;

namespace Core.Entities;

public class Product : ISoftDeletable, IAuditable
{{
    public int     Id       {{ get; set; }}
    public required string Name  {{ get; set; }}
    public string  Sku      {{ get; set; }} = "";
    public decimal Price    {{ get; set; }}
    public int     Stock    {{ get; set; }}

    // ISoftDeletable
    public bool      IsDeleted  {{ get; set; }}
    public DateTime? DeletedAt  {{ get; set; }}
    public string?   DeletedBy  {{ get; set; }}

    // IAuditable
    public DateTime CreatedAt {{ get; set; }}
    public DateTime UpdatedAt {{ get; set; }}
    public string   CreatedBy {{ get; set; }} = "";
    public string?  UpdatedBy {{ get; set; }}
}}
""", "Core/Entities/Product.cs")}

<h3>Step 3 — Interceptor (full code)</h3>
{C(r"""
using Core.Interfaces;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;

namespace Data.Interceptors;

public sealed class AuditAndSoftDeleteInterceptor(ICurrentUserService currentUser) : SaveChangesInterceptor
{{
    // Called synchronously
    public override InterceptionResult<int> SavingChanges(
        DbContextEventData eventData, InterceptionResult<int> result)
    {{
        Intercept(eventData.Context);
        return base.SavingChanges(eventData, result);
    }}

    // Called by SaveChangesAsync
    public override ValueTask<InterceptionResult<int>> SavingChangesAsync(
        DbContextEventData eventData, InterceptionResult<int> result,
        CancellationToken cancellationToken = default)
    {{
        Intercept(eventData.Context);
        return base.SavingChangesAsync(eventData, result, cancellationToken);
    }}

    private void Intercept(DbContext? context)
    {{
        if (context is null) return;
        var now  = DateTime.UtcNow;
        var user = currentUser.UserName;

        foreach (var entry in context.ChangeTracker.Entries())
        {{
            // ── Soft delete ──────────────────────────────────────────────
            if (entry.State == EntityState.Deleted && entry.Entity is ISoftDeletable sd)
            {{
                entry.State = EntityState.Modified;    // turn DELETE into UPDATE
                sd.IsDeleted  = true;
                sd.DeletedAt  = now;
                sd.DeletedBy  = user;

                // Don't stamp audit fields for a soft delete — treat it as the final update
                continue;
            }}

            // ── Audit fields ─────────────────────────────────────────────
            if (entry.Entity is IAuditable auditable)
            {{
                auditable.UpdatedAt = now;
                auditable.UpdatedBy = user;
                if (entry.State == EntityState.Added)
                {{
                    auditable.CreatedAt = now;
                    auditable.CreatedBy = user;
                }}
            }}
        }}
    }}
}}
""", "Data/Interceptors/AuditAndSoftDeleteInterceptor.cs")}

<h3>Step 4 — DbContext with global filter</h3>
{C(r"""
using Data.Interceptors;
using Core.Entities;
using Core.Interfaces;
using Microsoft.EntityFrameworkCore;

namespace Data;

public class AppDbContext : DbContext
{{
    public DbSet<Product> Products => Set<Product>();

    private readonly AuditAndSoftDeleteInterceptor _interceptor;

    public AppDbContext(DbContextOptions<AppDbContext> options,
                        AuditAndSoftDeleteInterceptor interceptor) : base(options)
    {{
        _interceptor = interceptor;
    }}

    protected override void OnConfiguring(DbContextOptionsBuilder options)
    {{
        options.AddInterceptors(_interceptor);
    }}

    protected override void OnModelCreating(ModelBuilder model)
    {{
        // Apply soft-delete filter to every ISoftDeletable entity
        foreach (var entityType in model.Model.GetEntityTypes())
        {{
            if (typeof(ISoftDeletable).IsAssignableFrom(entityType.ClrType))
                model.Entity(entityType.ClrType)
                     .HasQueryFilter(BuildIsDeletedFilter(entityType.ClrType));
        }}
    }}

    private static System.Linq.Expressions.LambdaExpression BuildIsDeletedFilter(Type type)
    {{
        var param = System.Linq.Expressions.Expression.Parameter(type, "e");
        var prop  = System.Linq.Expressions.Expression.Property(param, nameof(ISoftDeletable.IsDeleted));
        var body  = System.Linq.Expressions.Expression.Not(prop);
        return System.Linq.Expressions.Expression.Lambda(body, param);
    }}
}}
""", "Data/AppDbContext.cs")}

<h3>Step 5 — ICurrentUserService stub and wiring</h3>
{C(r"""
using Core.Interfaces;

namespace App.Services;

// In a real ASP.NET Core app this reads IHttpContextAccessor → User.Identity.Name
public class ConsoleUserService : ICurrentUserService
{{
    public string UserName => "system";   // stand-in for the logged-in user
}}
""", "App/Services/ConsoleUserService.cs")}
{C(r"""
using Core.Entities;
using Core.Interfaces;
using Data;
using Data.Interceptors;
using App.Services;
using Microsoft.EntityFrameworkCore;

var userSvc = new ConsoleUserService();
var interceptor = new AuditAndSoftDeleteInterceptor(userSvc);

var options = new DbContextOptionsBuilder<AppDbContext>()
    .UseSqlServer("Server=localhost,1433;Database=SoftDeleteDemo;User Id=sa;Password=Dev@Pass123;TrustServerCertificate=True")
    .Options;

await using var db = new AppDbContext(options, interceptor);
await db.Database.MigrateAsync();

// Add a product
db.Products.Add(new Product {{ Name = "Basmati Rice 5kg", Sku = "GR-001", Price = 649m, Stock = 200 }});
await db.SaveChangesAsync();

// Soft delete
var product = await db.Products.FirstAsync();
db.Products.Remove(product);              // EntityState.Deleted → interceptor changes to Modified
await db.SaveChangesAsync();

Console.WriteLine($"Soft-deleted. Count (with filter): {{await db.Products.CountAsync()}}");                 // 0
Console.WriteLine($"Count (without filter): {{await db.Products.IgnoreQueryFilters().CountAsync()}}");       // 1

// Confirm audit fields
var deleted = await db.Products.IgnoreQueryFilters().FirstAsync();
Console.WriteLine($"CreatedBy: {{deleted.CreatedBy}}, IsDeleted: {{deleted.IsDeleted}}, DeletedBy: {{deleted.DeletedBy}}");
// CreatedBy: system, IsDeleted: True, DeletedBy: system
""", "App/Program.cs")}
{C(r"""
dotnet ef migrations add InitialCreate -p Data -s App
dotnet ef database update -p Data -s App
dotnet run --project App
""", lang="bash")}
{C(r"""
-- Expected output (after MigrateAsync):
-- Soft-deleted. Count (with filter): 0
-- Count (without filter): 1
-- CreatedBy: system, IsDeleted: True, DeletedBy: system
""", lang="text")}

<h3>Stretch goals</h3>
{ul(["Add a <code>Category</code> entity that also implements both interfaces; verify the global filter and audit both work.",
"Add a <code>RestoreAsync(int id)</code> method that sets <code>IsDeleted = false</code> using <code>IgnoreQueryFilters + ExecuteUpdate</code>.",
"Replace the <code>ConsoleUserService</code> stub with one that reads an environment variable — simulating a CI pipeline identity.",
"Add an <code>AuditLog</code> table and a second interceptor that appends a row on every Add/Modify/Delete."])}
''',
iqs=[("Basic","What is the purpose of a SaveChangesInterceptor?","It runs code just before SaveChanges flushes to the database, letting you inspect and modify tracked entries — set audit timestamps, turn deletes into soft-deletes, validate business rules, or raise domain events."),
("Basic","Why convert EntityState.Deleted to EntityState.Modified in a soft-delete interceptor?","Leaving it as Deleted tells EF to issue a SQL DELETE, physically removing the row. Changing it to Modified causes EF to issue an UPDATE setting IsDeleted = true, keeping the row for history and audit."),
("Intermediate","How do you apply a global query filter dynamically to all entities that implement an interface?","Iterate modelBuilder.Model.GetEntityTypes(), check if each entity's ClrType implements the interface, and call modelBuilder.Entity(clrType).HasQueryFilter(lambdaExpression). The lambda is built at runtime with Expression.Lambda to match the entity's type."),
("Intermediate","What is the relationship between the interceptor and the implicit transaction?","The interceptor runs before EF flushes to the database, inside the implicit transaction. If SaveChanges fails (e.g. a constraint violation) the transaction rolls back, undoing the interceptor's mutations as well — there is no partial state.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "SQL inspection, EF performance checklist, try-to-break, README and quiz",
"Inspect the SQL behind six real queries, run a performance audit of the week's code, deliberately break concurrency and filter logic, write the README, commit, and test yourself.",
[("ToQueryString()","Returns the SQL string without executing the query. Available on IQueryable."),
("LogTo","Context option that routes EF logs to a delegate — use <code>LogLevel.Information</code> for SQL, <code>LogLevel.Debug</code> for all events."),
("QuerySingleOrDefaultAsync","Throws if more than one row is returned — use over <code>FirstOrDefault</code> when \"more than one\" is a bug."),
("No-tracking default","<code>UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking)</code> flips the default for the whole context; individual queries can re-enable with <code>AsTracking()</code>.")],
["Paste the generated SQL into SSMS or the MSSQL extension and check the execution plan — an index scan on a large table is usually a missing index.",
"Three red flags in EF logs: SELECT *, N+1, and <code>SELECT ... FROM (... subquery) AS t</code> applied to a large table without a sargable WHERE.",
"Include only what you use; every unused column is bytes on the wire and memory in .NET.",
"The best EF performance feature is often not EF at all — a covering index or a view in SQL Server."],
f'''
<h3>1. Six queries and their SQL</h3>
<p>Run each query and paste the <code>LogTo</code> output here as a study exercise. Expected forms are shown below.</p>

<h4>Q1 — Eager load with two levels</h4>
{C(r"""
var order = await db.Orders
    .Include(o => o.Customer)
    .Include(o => o.Lines).ThenInclude(l => l.Product)
    .AsNoTracking()
    .FirstOrDefaultAsync(o => o.Id == 1);
""", "Query1.cs")}
{C(r"""
SELECT TOP(1) [o].[Id], [o].[CustomerId], [o].[OrderDateUtc], [o].[Status], [o].[RowVersion],
       [c].[Id], [c].[City], [c].[Email], [c].[Name],
       [s].[Id], [s].[OrderId], [s].[ProductId], [s].[Quantity], [s].[UnitPrice],
       [s].[Id0], [s].[CategoryId], [s].[Name0], [s].[Price], [s].[Sku], [s].[Stock]
FROM [Orders] AS [o]
INNER JOIN [Customers] AS [c] ON [o].[CustomerId] = [c].[Id]
LEFT JOIN (
    SELECT [l].[Id], [l].[OrderId], [l].[ProductId], [l].[Quantity], [l].[UnitPrice],
           [p].[Id] AS [Id0], [p].[CategoryId], [p].[Name] AS [Name0], [p].[Price], [p].[Sku], [p].[Stock]
    FROM [OrderLines] AS [l]
    INNER JOIN [Products] AS [p] ON [l].[ProductId] = [p].[Id]
) AS [s] ON [o].[Id] = [s].[Id]
WHERE [o].[Id] = 1
ORDER BY [o].[Id], [c].[Id], [s].[Id]
""", "Q1 SQL (example)", lang="sql")}

<h4>Q2 — Projection to DTO (no entities loaded)</h4>
{C(r"""
var summaries = await db.Orders
    .AsNoTracking()
    .Select(o => new {{ o.Id, CustomerName = o.Customer.Name,
                        Total = o.Lines.Sum(l => l.Quantity * l.UnitPrice) }})
    .ToListAsync();
""", "Query2.cs")}
{C(r"""
SELECT [o].[Id], [c].[Name] AS [CustomerName],
       COALESCE((SELECT SUM([l].[Quantity] * [l].[UnitPrice])
                 FROM [OrderLines] AS [l] WHERE [o].[Id] = [l].[OrderId]), 0.0) AS [Total]
FROM [Orders] AS [o]
INNER JOIN [Customers] AS [c] ON [o].[CustomerId] = [c].[Id]
-- No ORDER BY: projection with no collection include → no key ordering needed
""", "Q2 SQL (example)", lang="sql")}

<h4>Q3 — ExecuteUpdate (no rows loaded)</h4>
{C(r"""
await db.Products.Where(p => p.Stock == 0).ExecuteUpdateAsync(s =>
    s.SetProperty(p => p.IsDeleted, true)
     .SetProperty(p => p.DeletedAt, DateTime.UtcNow));
""", "Query3.cs")}
{C(r"""
UPDATE [p]
SET [p].[IsDeleted] = CAST(1 AS bit),
    [p].[DeletedAt] = @__UtcNow_0
FROM [Products] AS [p]
WHERE [p].[Stock] = 0 AND [p].[IsDeleted] = 0   -- global filter still applies
""", "Q3 SQL (example)", lang="sql")}

<h4>Q4 — Global filter visible in SQL</h4>
{C(r"""
var active = await db.Products.CountAsync();
var all    = await db.Products.IgnoreQueryFilters().CountAsync();
Console.WriteLine($"Active: {{active}}, All: {{all}}");
""", "Query4.cs")}
{C(r"""
-- Query 4a (with filter):
SELECT COUNT(*)  FROM [Products] AS [p]  WHERE [p].[IsDeleted] = 0

-- Query 4b (IgnoreQueryFilters):
SELECT COUNT(*)  FROM [Products] AS [p]
""", "Q4 SQL (example)", lang="sql")}

<h4>Q5 — Concurrency: the UPDATE WHERE clause</h4>
{C(r"""
var order = await db.Orders.FirstAsync(o => o.Id == 1);
order.Status = OrderStatus.Shipped;
await db.SaveChangesAsync();   // prints the SQL below
""", "Query5.cs")}
{C(r"""
UPDATE [Orders]
SET [Status] = @p0
WHERE [Id] = @p1 AND [RowVersion] = @p2;    -- rowversion in the WHERE
SELECT [RowVersion]                          -- read back the new value
FROM [Orders]
WHERE @@ROWCOUNT = 1 AND [Id] = @p1;
""", "Q5 SQL (example)", lang="sql")}

<h4>Q6 — Split query (two round trips)</h4>
{C(r"""
var orders = await db.Orders
    .Include(o => o.Lines)
    .Include(o => o.Customer)
    .AsSplitQuery()
    .Take(10)
    .ToListAsync();
""", "Query6.cs")}
{C(r"""
-- Round trip 1: Orders + Customers
SELECT TOP(10) [o].[Id], [o].[CustomerId], [o].[OrderDateUtc], [o].[Status], [o].[RowVersion],
       [c].[Id], [c].[City], [c].[Email], [c].[Name]
FROM [Orders] AS [o]
INNER JOIN [Customers] AS [c] ON [o].[CustomerId] = [c].[Id]
ORDER BY [o].[Id]

-- Round trip 2: Lines for the same 10 orders
SELECT [l].[Id], [l].[OrderId], [l].[ProductId], [l].[Quantity], [l].[UnitPrice], [o0].[Id]
FROM [Orders] AS [o0]
INNER JOIN [OrderLines] AS [l] ON [o0].[Id] = [l].[OrderId]
WHERE [o0].[Id] IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
ORDER BY [o0].[Id]
""", "Q6 SQL (example)", lang="sql")}

<h3>2. EF performance checklist</h3>
{table(["Check","How to verify"],[
["No N+1: list queries use Include or projection","Count SQL statements in LogTo"],
["Read-only queries use AsNoTracking","Grep for AsNoTracking in controller/service layer"],
["Projections pull only needed columns","Read Q2 SQL: no SELECT *"],
["Collections with cartesian risk use AsSplitQuery","Search for double Include of collections"],
["ExecuteUpdate/Delete for bulk ops","No ToList() + foreach + SaveChanges for bulk changes"],
["Indexes on FK columns and common WHERE fields","Run sp_helpindex or check SSMS missing index suggestions"],
["global query filters are correct","Query with and without IgnoreQueryFilters; compare counts"],
["No lazy loading in production","grep for UseLazyLoadingProxies in startup"],
["Compiled queries for &gt;1k calls/sec hot path","Profiler + load test"]])}

<h3>3. Try to break it</h3>
{table(["Scenario","Expected behaviour","Why"],[
["Two contexts update same Order simultaneously","<code>DbUpdateConcurrencyException</code> on second save","RowVersion mismatch — 0 rows affected"],
["Call <code>db.Products.Remove(p)</code> on a soft-deletable","UPDATE IsDeleted = 1, row still in DB","Interceptor flips EntityState.Deleted → Modified"],
["Query Products without IgnoreQueryFilters after soft delete","Returns 0 rows","Global filter adds WHERE IsDeleted = 0"],
["Call <code>SaveChanges</code> inside an execution strategy's lambda that uses <code>BeginTransaction</code>","Works correctly — strategy wraps the lambda","ExecuteAsync controls the retry boundary"],
["<code>Include</code> two collections without AsSplitQuery with 10+ rows each","Row count = product of child counts per order","Cartesian explosion — observe in LogTo"],
["Change enum HasConversion from int to string on existing DB","Migration fails unless you migrate data first","Column type change is breaking"]])}

<h3>4. README template</h3>
{C(r"""
# Week 16 — EF Core in Depth

## What was built
- Extended StoreDb with Customers / Orders / OrderLines (Week 15 continuation)
- SoftDeleteAuditDemo console project: ISoftDeletable + IAuditable + interceptor

## Key techniques practised
- Eager / explicit / lazy loading; filtered Include
- N+1 detection with LogTo; AsNoTracking + projections
- Raw SQL: FromSql, SqlQuery, ExecuteUpdate/Delete, stored procs
- Optimistic concurrency with rowversion; explicit transactions; execution strategies
- Owned types, value conversions, global query filters, shadow properties, HasData

## Run instructions
```bash
# Start SQL Server 2022
docker run -e ACCEPT_EULA=Y -e MSSQL_SA_PASSWORD=Dev@Pass123 \
  -p 1433:1433 -d mcr.microsoft.com/mssql/server:2022-latest

# StoreDb (loading / concurrency / raw SQL demos)
cd StoreDb
dotnet ef database update -p Store.Data -s Store.App
dotnet run --project Store.App

# SoftDeleteAuditDemo
cd ../SoftDeleteAuditDemo
dotnet ef database update -p Data -s App
dotnet run --project App
```
""", "README.md", lang="text")}
{C(r"""
cd week16
git add .
git commit -m "Week 16: EF Core in depth — loading, raw SQL, concurrency, interceptors"
git push
""", lang="bash")}

<h3>5. Week revision checklist</h3>
<ul>
<li>Include / ThenInclude — which navigation triggers INNER vs LEFT JOIN?</li>
<li>Filtered Include limitations — fix-up gotcha, tracking vs no-tracking</li>
<li>N+1 — how to detect (LogTo) and fix (Include or projection)</li>
<li>AsNoTracking vs AsNoTrackingWithIdentityResolution</li>
<li>AsSplitQuery — when and why (cartesian explosion)</li>
<li>FromSql vs FromSqlRaw — which is safer with interpolated strings?</li>
<li>ExecuteUpdate / ExecuteDelete — bypasses what?</li>
<li>Stored procs — SqlQuery vs ExecuteSqlRaw</li>
<li>[Timestamp] / rowversion — what SQL is added to UPDATE/DELETE?</li>
<li>DbUpdateConcurrencyException — three resolution strategies</li>
<li>BeginTransaction + execution strategy — why they can't be nested directly</li>
<li>Owned types — same table, no DbSet, can have OwnsMany</li>
<li>Value conversions — where do they execute? Can LINQ filter them?</li>
<li>Global query filters — apply to Includes? How to bypass?</li>
<li>Shadow properties — how to set, how to query</li>
<li>HasData vs custom seeding — which requires explicit PKs?</li>
<li>SaveChangesInterceptor — SavingChanges vs SavingChangesAsync overrides</li>
<li>Soft delete interceptor — EntityState.Deleted → EntityState.Modified</li>
</ul>

<h3>6. Quiz — predict the output / does it compile?</h3>
<details><summary>Q1. How many SQL statements does this code send?</summary>
{C(r"""
await using var db = Db.Create(logSql: false);
var customers = await db.Customers.ToListAsync();
int total = 0;
foreach (var c in customers)
    total += c.Orders.Count;
Console.WriteLine(total);
""")}
<b>1 + N (where N = number of customers).</b> <code>c.Orders</code> is not loaded; each access returns the empty list (0), so total is always 0 — but only because tracking is on and the Orders property was never loaded. If lazy loading were enabled it would fire N queries. Fix: <code>Include(c =&gt; c.Orders)</code> or project to a count DTO.
</details>
<details><summary>Q2. Does this compile and what does it do?</summary>
{C(r"""
await db.Products.Where(p => p.Name.StartsWith("B"))
                 .ExecuteUpdateAsync(s =>
                     s.SetProperty(p => p.Stock, p => p.Stock - 1));
""")}
<b>Yes, compiles and runs.</b> Sends one SQL: <code>UPDATE Products SET Stock = Stock - 1 WHERE Name LIKE 'B%' AND IsDeleted = 0</code>. No entities are loaded. The global query filter still applies (adds the IsDeleted check).
</details>
<details><summary>Q3. What exception type is thrown and why?</summary>
{C(r"""
await using var db1 = Db.Create();
await using var db2 = Db.Create();
var o1 = await db1.Orders.FindAsync(1);
var o2 = await db2.Orders.FindAsync(1);
o1!.Status = OrderStatus.Shipped;
o2!.Status = OrderStatus.Cancelled;
await db1.SaveChangesAsync();
await db2.SaveChangesAsync();   // ?
""")}
<b>DbUpdateConcurrencyException.</b> db1's save bumps the rowversion. db2's UPDATE WHERE RowVersion = @orig finds 0 rows; EF detects this and throws.
</details>
<details><summary>Q4. What does the global filter add to this query?</summary>
{C(r"""
var products = await db.Products
    .Where(p => p.Price > 500)
    .OrderBy(p => p.Name)
    .ToListAsync();
""")}
<b>WHERE Price &gt; 500 AND IsDeleted = 0</b> (or whatever the filter predicate is). EF ANDs the global filter onto every query automatically.
</details>
<details><summary>Q5. Does this compile? What happens at runtime?</summary>
{C(r"""
var order = await db.Orders.AsNoTracking().FirstAsync();
order.Status = OrderStatus.Shipped;
await db.SaveChangesAsync();
""")}
<b>Compiles. SaveChanges sends 0 SQL statements and returns 0.</b> The entity is untracked; EF has no record of it and nothing to flush. No exception is thrown. This is a common silent bug.
</details>

{tip("Next week: ASP.NET Core fundamentals — Minimal APIs, middleware pipeline, dependency injection, configuration, and your first to-do API backed by this week's EF setup.")}
''',
iqs=[("Basic","What does ToQueryString() return?","The SQL string the LINQ query will execute, without actually running it. Available on IQueryable. Great for learning and debugging — paste the output into SSMS to see the execution plan."),
("Basic","Name three signs of an EF performance problem in the logs.","(1) Multiple SELECT ... WHERE ForeignKeyId = @p statements in a loop — N+1. (2) SELECT with no WHERE on a large table — full table scan. (3) Very large result set with many duplicate columns — cartesian explosion from multiple collection Includes."),
("Intermediate","Why does SaveChanges return 0 for an AsNoTracking entity?","AsNoTracking entities are not registered in the ChangeTracker. SaveChanges only flushes tracked entries in Added, Modified or Deleted state. An untracked entity has no state, so SaveChanges has nothing to do — silent no-op."),
("Intermediate","How does the soft-delete interceptor interact with ExecuteDelete?","SaveChangesInterceptor only fires for changes tracked by the ChangeTracker (entries going through SaveChanges). ExecuteDelete bypasses the ChangeTracker and runs a SQL DELETE directly — the interceptor is never called. Use ExecuteUpdate to soft-delete in bulk: set IsDeleted = true, DeletedAt = now explicitly.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Loading related data","Include &amp; loading","Include/ThenInclude, filtered Include, explicit, lazy loading, SQL produced.","2 hrs"),
 (2,"TUE","N+1, tracking and projections","N+1 · NoTracking","Detecting N+1 with LogTo, AsNoTracking, DTOs, AsSplitQuery.","2 hrs"),
 (3,"WED","Raw SQL and bulk operations","Raw SQL","FromSql, SqlQuery, ExecuteUpdate/Delete, stored procs, compiled queries.","2 hrs"),
 (4,"THU","Concurrency and transactions","Concurrency · Tx","rowversion, DbUpdateConcurrencyException, BeginTransaction, retry strategies.","2 hrs"),
 (5,"FRI","Owned types, conversions, filters","Owned · Filters","Owned types, value conversions, global filters, shadow props, HasData.","2 hrs"),
 (6,"SAT","Soft delete + audit interceptor","Project: interceptor","ISoftDeletable/IAuditable, full SaveChangesInterceptor, global filter, migration.","4 hrs"),
 (7,"SUN","SQL inspection, checklist and quiz","Revision &amp; quiz","Six SQL blocks, perf checklist, try-to-break, README, git, quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week16.html", 16,
      "Week 16 — EF Core in Depth",
      "Phase 2", "~18 hrs",
      ["Phase 2 · Week 16 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "Soft delete + audit"],
      "EF Core is powerful enough to get you into trouble without knowing it. This week you go deep: loading strategies and their SQL, N+1 detection and fixes, raw SQL for when LINQ isn't enough, optimistic concurrency with rowversion, owned types and global filters, and a production-quality soft-delete and audit interceptor as the weekend project.",
      cards, days)
print("built")
