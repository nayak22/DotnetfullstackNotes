import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1  MON =================
d1 = day(1, "MON", "ADO.NET: SqlConnection, SqlCommand, SqlDataReader",
"Open a real SQL Server connection with Microsoft.Data.SqlClient, run queries safely with parameters, and understand async patterns and connection pooling.",
[("ADO.NET","Active Data Objects .NET — the low-level data-access API; every higher ORM sits on top of it."),
("Microsoft.Data.SqlClient","The modern cross-platform SQL Server driver (NuGet); replaces the old System.Data.SqlClient."),
("SqlConnection","Represents one connection to SQL Server; opening it checks out a pooled connection."),
("SqlCommand","Encapsulates a T-SQL statement or stored procedure to run against a connection."),
("SqlDataReader","A fast, forward-only cursor over result rows; call Read() once per row."),
("ExecuteScalar","Runs a command and returns the first column of the first row as object; good for COUNT/SUM."),
("ExecuteNonQuery","Runs INSERT/UPDATE/DELETE; returns the number of rows affected."),
("ExecuteReader","Runs a SELECT and returns a SqlDataReader."),
("Parameters","Typed values attached to a SqlCommand via SqlParameters; prevent SQL injection."),
("SQL injection","Attacker injects T-SQL by embedding it in a string concatenation; parameters stop it."),
("Connection pooling","ADO.NET reuses physical connections; opening/closing SqlConnection is cheap by design."),
("TrustServerCertificate","Connection-string key needed for local Docker SQL Server that uses a self-signed cert."),
("await using","Disposes an IAsyncDisposable asynchronously; use on SqlConnection and SqlCommand in async code.")],
["Always use <code>await using</code> (or a <code>using</code> block) to close connections back to the pool.",
"<b>Never</b> concatenate user input into T-SQL strings; always use <code>SqlParameter</code>.",
"<code>CommandTimeout</code> defaults to 30 s; set it higher for reports, lower for OLTP.",
"<code>SqlDataReader</code> is forward-only and must be closed before the connection can run another command.",
"<code>ExecuteScalar</code> returns <code>null</code> if the result set is empty; cast to <code>object</code> then check."],
f'''
<h3>1. Connection string and first query</h3>
{C(r"""
// NuGet: Microsoft.Data.SqlClient
using Microsoft.Data.SqlClient;

const string ConnStr =
    "Server=localhost,1433;Database=StoreDb;User Id=sa;Password=YourStrong!Pass;" +
    "TrustServerCertificate=True;";   // needed when Docker uses a self-signed cert

await using var conn = new SqlConnection(ConnStr);
await conn.OpenAsync();             // checks out a pooled connection

const string sql = "SELECT ProductId, Name, Price FROM Products WHERE CategoryId = @catId";
await using var cmd = new SqlCommand(sql, conn);
cmd.Parameters.AddWithValue("@catId", 2);     // safe: parameterised

await using var reader = await cmd.ExecuteReaderAsync();
while (await reader.ReadAsync())
{
    int    id    = reader.GetInt32(0);
    string name  = reader.GetString(1);
    decimal price = reader.GetDecimal(2);
    Console.WriteLine($"  {id,4}  {name,-30}  ₹{price,8:N2}");
}
""", "BasicQuery.cs")}
{tip("The connection string key <code>TrustServerCertificate=True</code> is fine for a local Docker instance. For production, use a properly signed certificate instead.")}

<h3>2. SQL injection — attack and fix</h3>
{C(r"""
// ❌ VULNERABLE — attacker sends name = "'; DROP TABLE Products; --"
string userInput = Console.ReadLine()!;
string badSql = $"SELECT * FROM Products WHERE Name = '{userInput}'";
// Resulting T-SQL:  SELECT * FROM Products WHERE Name = ''; DROP TABLE Products; --'

// ✓ SAFE — parameter binding
await using var conn = new SqlConnection(ConnStr);
await conn.OpenAsync();
await using var cmd = new SqlCommand(
    "SELECT ProductId, Name FROM Products WHERE Name = @name", conn);
cmd.Parameters.Add("@name", System.Data.SqlDbType.NVarChar, 200).Value = userInput;

await using var reader = await cmd.ExecuteReaderAsync();
while (await reader.ReadAsync())
    Console.WriteLine(reader.GetString(1));
""", "SqlInjection.cs")}
{warn("Never use <code>Parameters.AddWithValue</code> for binary/date types — the driver infers the wrong SqlDbType. Use <code>Parameters.Add(name, SqlDbType.Date).Value = val</code> for explicit types.", "Best practice")}

<h3>3. ExecuteScalar and ExecuteNonQuery</h3>
{C(r"""
// ExecuteScalar — scalar result
await using var conn = new SqlConnection(ConnStr);
await conn.OpenAsync();

await using var countCmd = new SqlCommand(
    "SELECT COUNT(*) FROM Orders WHERE CustomerId = @cid AND OrderDate >= @from", conn);
countCmd.Parameters.Add("@cid",  System.Data.SqlDbType.Int).Value       = 101;
countCmd.Parameters.Add("@from", System.Data.SqlDbType.Date).Value      = new DateTime(2026, 1, 1);
object? raw = await countCmd.ExecuteScalarAsync();
int count = raw is null ? 0 : Convert.ToInt32(raw);
Console.WriteLine($"Orders this year: {count}");

// ExecuteNonQuery — INSERT, UPDATE, DELETE
await using var insCmd = new SqlCommand(
    "INSERT INTO Products (Name, Price, CategoryId) VALUES (@n, @p, @c)", conn);
insCmd.Parameters.Add("@n", System.Data.SqlDbType.NVarChar, 200).Value  = "Wireless Mouse";
insCmd.Parameters.Add("@p", System.Data.SqlDbType.Decimal).Value        = 799m;
insCmd.Parameters.Add("@c", System.Data.SqlDbType.Int).Value            = 3;
int rows = await insCmd.ExecuteNonQueryAsync();
Console.WriteLine($"{rows} row(s) inserted");   // 1 row(s) inserted
""", "ScalarNonQuery.cs")}

<h3>4. Reading the new IDENTITY back</h3>
{C(r"""
// Append OUTPUT INSERTED.Id to get the generated PK in one round trip
const string insertSql = @"
    INSERT INTO Products (Name, Price, CategoryId)
    OUTPUT INSERTED.ProductId
    VALUES (@n, @p, @c)";

await using var conn = new SqlConnection(ConnStr);
await conn.OpenAsync();
await using var cmd = new SqlCommand(insertSql, conn);
cmd.Parameters.Add("@n", System.Data.SqlDbType.NVarChar, 200).Value = "Bluetooth Keyboard";
cmd.Parameters.Add("@p", System.Data.SqlDbType.Decimal).Value        = 1299m;
cmd.Parameters.Add("@c", System.Data.SqlDbType.Int).Value            = 3;

object? inserted = await cmd.ExecuteScalarAsync();
int newId = Convert.ToInt32(inserted);
Console.WriteLine($"New product id: {newId}");
""", "InsertAndGetId.cs")}

<h3>5. Connection pooling explained</h3>
<ol>
<li>The <i>first</i> <code>Open()</code> creates a real TCP connection to SQL Server.</li>
<li>On <code>Close()</code> / <code>Dispose()</code>, ADO.NET returns it to an in-process pool keyed by connection string.</li>
<li>The <i>next</i> <code>Open()</code> with the same string reuses that physical connection — typically &lt;1 ms vs ~50 ms for a new one.</li>
<li>Default pool: 1–100 connections. Tune with <code>Min Pool Size</code> and <code>Max Pool Size</code> in the string.</li>
</ol>
{C(r"""
// All three share the pool — physical connections are reused
for (int i = 0; i < 5; i++)
{
    await using var c = new SqlConnection(ConnStr);
    await c.OpenAsync();                            // fast after first open
    Console.WriteLine($"State: {c.State}");         // Open
}   // Dispose() returns to pool, does NOT close the TCP connection
""", "PoolDemo.cs")}
{warn("Setting <code>Pooling=False</code> in the connection string disables pooling — every Open creates a new TCP connection. Never do this in production OLTP code.", "Avoid")}

<h3>6. Async pattern: async/await from top to bottom</h3>
{C(r"""
public static async Task<IReadOnlyList<Product>> GetByCategoryAsync(int categoryId,
    CancellationToken ct = default)
{
    var results = new List<Product>();

    await using var conn = new SqlConnection(ConnStr);
    await conn.OpenAsync(ct);

    await using var cmd = new SqlCommand(
        "SELECT ProductId, Name, Price FROM Products WHERE CategoryId = @cid ORDER BY Name", conn);
    cmd.Parameters.Add("@cid", System.Data.SqlDbType.Int).Value = categoryId;

    await using var reader = await cmd.ExecuteReaderAsync(ct);
    while (await reader.ReadAsync(ct))
    {
        results.Add(new Product(
            reader.GetInt32(0),
            reader.GetString(1),
            reader.GetDecimal(2)));
    }
    return results;
}

public record Product(int Id, string Name, decimal Price);
""", "DataAccess.cs")}
{tip("Pass a <code>CancellationToken</code> from your controller or top-level host all the way into <code>OpenAsync</code> and <code>ReadAsync</code>. When the HTTP client disconnects, the query is cancelled and the connection returns to the pool immediately.")}
''',
["Forgetting <code>TrustServerCertificate=True</code> for a local Docker instance and getting a certificate error.",
"Building SQL strings with <code>$\"...{userInput}...\"</code> — use parameters.",
"Reading <code>reader.GetString(0)</code> when the column is <code>NULL</code> — check <code>reader.IsDBNull(0)</code> first.",
"Not disposing the reader before reusing the connection (a second command on the same connection while a reader is open throws <code>InvalidOperationException</code>).",
"Storing the connection as a singleton field — pool a string, not an open connection."],
("40 min", [
"Create <code>StoreDb</code> in Docker (commands on Saturday). Write a console app that reads Products and prints them in a formatted table with ₹ prices.",
"Add a method <code>InsertProductAsync(string name, decimal price, int categoryId)</code> that inserts a row and returns the new ProductId using <code>OUTPUT INSERTED.ProductId</code>.",
"Demonstrate the injection attack in a debug build (print the bad SQL to the console), then switch to parameters and show the safe version."]),
[("What does <code>await using</code> do?","It calls <code>DisposeAsync()</code> after the block, returning the connection to the pool asynchronously."),
("Why shouldn't you hold a SqlConnection open across a long operation?","It holds a physical connection from the pool. Under load, other threads starve waiting for a free connection."),
("What is <code>ExecuteScalar</code> good for?","Single-value queries: COUNT, MAX, MIN, a newly inserted IDENTITY. Returns <code>null</code> if the result set is empty.")],
[("Basic","What is ADO.NET?","The base data-access layer in .NET. It provides SqlConnection, SqlCommand, SqlDataReader and DataAdapter. ORMs like Dapper and EF Core are built on top of it."),
("Basic","How do SqlParameters prevent SQL injection?","The driver serialises the value separately from the query text. The value is never interpreted as T-SQL, so appending <code>; DROP TABLE Products</code> is just a string value."),
("Basic","Explain connection pooling in ADO.NET.","When you call Dispose/Close, the physical TCP connection is kept alive in a pool keyed by connection string. The next Open with the same string reuses it, avoiding the ~50 ms cost of a fresh TCP handshake and login."),
("Intermediate","What is the difference between ExecuteScalar, ExecuteNonQuery and ExecuteReader?","ExecuteScalar returns one value (first column, first row) — good for COUNT/SUM. ExecuteNonQuery runs DML and returns the rows-affected count. ExecuteReader opens a forward-only cursor for multi-row SELECT results."),
("Intermediate","When would you use <code>CommandBehavior.CloseConnection</code>?","When you want the connection auto-closed when the reader is closed — useful when you return the reader from a method so the caller doesn't need to manage the connection explicitly. With async/await and proper disposal this is rarely needed."),
("Intermediate","What is the risk of <code>Parameters.AddWithValue</code>?","The driver infers the SqlDbType from the .NET value. A string infers NVarChar(4000) but your column might be Varchar(50), causing an index-scan rather than a seek. Use <code>Parameters.Add(name, SqlDbType.NVarChar, 50)</code> to be precise.")])

# ================= DAY 2  TUE =================
d2 = day(2, "TUE", "Dapper: micro-ORM on top of ADO.NET",
"Use Dapper to map query results directly into C# objects with minimal ceremony, run multi-mapping, stored procedures and IN-list queries.",
[("Dapper","A micro-ORM that extends <code>IDbConnection</code> with extension methods like <code>Query&lt;T&gt;</code> and <code>Execute</code>."),
("Query&lt;T&gt;","Runs a SELECT and materialises each row into a strongly-typed T using property-name matching."),
("QueryAsync&lt;T&gt;","The async variant of Query, returning <code>IEnumerable&lt;T&gt;</code> (materialised on return)."),
("Execute","Runs INSERT/UPDATE/DELETE; accepts an anonymous object for parameters."),
("Anonymous params","An anonymous object <code>new { Name = x, Price = y }</code> whose property names match SQL parameter names."),
("Multi-mapping","<code>Query&lt;TFirst, TSecond, TReturn&gt;</code> joins two tables and maps them into separate objects."),
("QueryMultiple","Runs multiple SELECT statements in one round trip and reads each result set sequentially."),
("Stored procedure","A compiled T-SQL routine; Dapper calls it with <code>commandType: CommandType.StoredProcedure</code>."),
("IN-list","A variable number of values after IN (); Dapper expands a C# collection into <code>(@p0,@p1,...)</code>."),
("DynamicParameters","Dapper's typed parameter bag; supports OUTPUT parameters and table-valued parameters.")],
["Dapper maps by <b>property name</b> (case-insensitive) — column alias in SQL to match the property name when they differ.",
"Dapper materialises the result set before returning, so you can close the connection immediately after the call.",
"Use <code>QueryFirstOrDefaultAsync&lt;T&gt;</code> when you expect at most one row.",
"Dapper's IN-list expansion sends <code>@ids0, @ids1, …</code> — this prevents injection but generates a unique plan per list size.",
"<code>DynamicParameters</code> is needed for OUTPUT params and stored procedures that have both IN and OUT."],
f'''
<h3>1. Installing and first query</h3>
{C(r"""
// NuGet: Dapper  (also requires Microsoft.Data.SqlClient)
using Dapper;
using Microsoft.Data.SqlClient;

const string ConnStr = "Server=localhost,1433;Database=StoreDb;User Id=sa;" +
                       "Password=YourStrong!Pass;TrustServerCertificate=True;";

await using var conn = new SqlConnection(ConnStr);

// Query<T> maps column names to property names (case-insensitive)
IEnumerable<Product> products =
    await conn.QueryAsync<Product>("SELECT ProductId, Name, Price FROM Products ORDER BY Price");

foreach (var p in products)
    Console.WriteLine($"  {p.ProductId,4}  {p.Name,-30}  ₹{p.Price,8:N2}");

// Get a single row (null when not found)
Product? item = await conn.QueryFirstOrDefaultAsync<Product>(
    "SELECT ProductId, Name, Price FROM Products WHERE ProductId = @id",
    new { id = 7 });

Console.WriteLine(item is null ? "Not found" : $"Found: {item.Name}");

public class Product
{
    public int     ProductId  { get; set; }
    public string  Name       { get; set; } = "";
    public decimal Price      { get; set; }
}
""", "DapperBasics.cs")}

<h3>2. Execute — INSERT/UPDATE/DELETE with anonymous params</h3>
{C(r"""
await using var conn = new SqlConnection(ConnStr);

// Anonymous object: property names become @name, @price, @categoryId
int inserted = await conn.ExecuteAsync(
    "INSERT INTO Products (Name, Price, CategoryId) VALUES (@name, @price, @categoryId)",
    new { name = "Wireless Earbuds", price = 1899m, categoryId = 4 });

Console.WriteLine($"Inserted {inserted} row(s)");   // 1

// Batch insert: pass a collection — Dapper loops and runs one statement per item
var newItems = new[]
{
    new { name = "USB Hub",  price = 599m, categoryId = 3 },
    new { name = "Web Cam",  price = 2499m, categoryId = 3 },
};
int total = await conn.ExecuteAsync(
    "INSERT INTO Products (Name, Price, CategoryId) VALUES (@name, @price, @categoryId)",
    newItems);
Console.WriteLine($"Batch inserted {total} row(s)");   // 2
""", "DapperExecute.cs")}
{tip("Dapper batch inserts loop in C#, not in a single SQL statement. For large volumes, use <code>SqlBulkCopy</code> or a table-valued parameter.")}

<h3>3. Multi-mapping: JOIN two tables into two objects</h3>
{C(r"""
const string joinSql = @"
    SELECT p.ProductId, p.Name, p.Price,
           c.CategoryId, c.CategoryName
    FROM   Products p
    JOIN   Categories c ON c.CategoryId = p.CategoryId
    ORDER  BY c.CategoryName, p.Name";

await using var conn = new SqlConnection(ConnStr);

// First 3 columns → Product; next 2 → Category
IEnumerable<Product> rows = await conn.QueryAsync<Product, Category, Product>(
    joinSql,
    map: (product, category) => { product.Category = category; return product; },
    splitOn: "CategoryId");   // Dapper splits at the first column named CategoryId

foreach (var p in rows)
    Console.WriteLine($"  [{p.Category?.CategoryName}] {p.Name}  ₹{p.Price:N2}");

public class Category
{
    public int    CategoryId   { get; set; }
    public string CategoryName { get; set; } = "";
}

public class Product
{
    public int      ProductId  { get; set; }
    public string   Name       { get; set; } = "";
    public decimal  Price      { get; set; }
    public Category? Category  { get; set; }
}
""", "DapperMultimap.cs")}

<h3>4. QueryMultiple — two result sets in one round trip</h3>
{C(r"""
const string twoSelects = @"
    SELECT ProductId, Name, Price FROM Products WHERE CategoryId = @catId;
    SELECT COUNT(*) FROM Products WHERE CategoryId = @catId;";

await using var conn = new SqlConnection(ConnStr);
using var multi = await conn.QueryMultipleAsync(twoSelects, new { catId = 2 });

IEnumerable<Product> products = await multi.ReadAsync<Product>();
int total = await multi.ReadSingleAsync<int>();

Console.WriteLine($"Category 2 has {total} product(s):");
foreach (var p in products)
    Console.WriteLine($"  {p.Name}  ₹{p.Price:N2}");
""", "DapperQueryMultiple.cs")}

<h3>5. Stored procedures</h3>
{C(r"""
// T-SQL proc definition (run once to create it):
// CREATE PROCEDURE usp_GetOrdersByCustomer
//   @CustomerId INT, @From DATE, @To DATE
// AS
//   SELECT o.OrderId, o.OrderDate, o.TotalAmount
//   FROM   Orders o
//   WHERE  o.CustomerId = @CustomerId
//     AND  o.OrderDate BETWEEN @From AND @To;

await using var conn = new SqlConnection(ConnStr);
var orders = await conn.QueryAsync<Order>(
    "usp_GetOrdersByCustomer",
    new { CustomerId = 101, From = new DateTime(2026, 1, 1), To = DateTime.Today },
    commandType: System.Data.CommandType.StoredProcedure);

foreach (var o in orders)
    Console.WriteLine($"  #{o.OrderId}  {o.OrderDate:dd-MMM-yyyy}  ₹{o.TotalAmount:N2}");

public record Order(int OrderId, DateTime OrderDate, decimal TotalAmount);
""", "DapperStoredProc.cs")}

<h3>6. IN-list queries</h3>
{C(r"""
// Dapper expands the collection automatically:  WHERE ProductId IN (@ids0, @ids1, @ids2)
var ids = new[] { 3, 7, 12, 19 };
await using var conn = new SqlConnection(ConnStr);
IEnumerable<Product> found = await conn.QueryAsync<Product>(
    "SELECT ProductId, Name, Price FROM Products WHERE ProductId IN @ids",
    new { ids });   // Note: no parentheses — Dapper adds them

foreach (var p in found)
    Console.WriteLine($"  {p.ProductId}  {p.Name}  ₹{p.Price:N2}");
""", "DapperInList.cs")}
{warn("SQL Server has an IN-list limit of 2 100 parameters by default. For large sets, batch into groups of 1000 or use a table-valued parameter.", "Limit")}
''',
["Forgetting <code>splitOn</code> in multi-mapping (default is 'Id'; use the actual column name).",
"Calling <code>Query&lt;T&gt;</code> (synchronous) in an async method instead of <code>QueryAsync&lt;T&gt;</code>.",
"Mismatch between SQL column alias and C# property name — alias the column in SQL to match.",
"Passing a large collection to IN-list without batching, hitting the 2100-parameter limit.",
"Forgetting <code>commandType: CommandType.StoredProcedure</code> — the default is Text, which wraps the proc name in a SELECT."],
("40 min", [
"Write <code>ProductRepository</code> with methods <code>GetAllAsync</code>, <code>GetByIdAsync</code>, <code>InsertAsync</code> using Dapper.",
"Add a method that queries Orders with their customer names using multi-mapping (JOIN on <code>CustomerId</code>).",
"Add a <code>GetByIdsAsync(IEnumerable&lt;int&gt; ids)</code> method using the IN-list feature."]),
[("How does Dapper map columns to properties?","By property name, case-insensitively. If the name differs, alias the column in SQL: <code>ProductId AS Id</code>."),
("What is QueryMultiple used for?","Sending several SELECT statements in one network round trip, then reading each result set in order with <code>Read&lt;T&gt;</code>."),
("How does Dapper handle IN-list parameters?","A collection property (e.g., <code>new { ids = new[] {1,2,3} }</code>) is expanded to <code>(@ids0, @ids1, @ids2)</code> automatically.")],
[("Basic","What is Dapper and how does it relate to ADO.NET?","Dapper is a micro-ORM — a set of extension methods on IDbConnection. It sits directly on ADO.NET, using SqlCommand internally but handling the reader-to-object mapping for you, with minimal overhead."),
("Basic","Dapper vs EF Core: when would you pick each?","Dapper for maximum control over SQL, raw performance, complex reports or existing stored procedures. EF Core for create/update/delete, change tracking, migrations and teams that prefer not to write SQL by hand."),
("Basic","How do you call a stored procedure with Dapper?","Pass the procedure name as the SQL, and <code>commandType: CommandType.StoredProcedure</code>. Parameters match by name."),
("Intermediate","What is <code>DynamicParameters</code> and when do you need it?","A typed bag for Dapper parameters that supports OUTPUT and RETURN values: <code>var dp = new DynamicParameters(); dp.Add(\"@NewId\", dbType: DbType.Int32, direction: ParameterDirection.Output);</code> then read with <code>dp.Get&lt;int&gt;(\"@NewId\")</code>. Required for stored procedures that return values via OUTPUT params."),
("Intermediate","How does Dapper's batch Execute work?","Passing an IEnumerable as the param argument makes Dapper iterate and run the statement once per item in a loop. It is NOT a single bulk SQL — use SqlBulkCopy or TVPs for high-volume inserts."),
("Intermediate","Can Dapper be used with transactions?","Yes. Pass the transaction as the <code>transaction</code> argument: <code>conn.Execute(sql, params, transaction: tx)</code>. The connection and transaction must both be open and must match.")])

# ================= DAY 3  WED =================
d3 = day(3, "WED", "EF Core: DbContext, DbSet, UseSqlServer, migrations",
"Define a model, wire up EF Core, add the first migration, and apply it to create the schema — the foundation every day this week builds on.",
[("DbContext","EF Core's unit-of-work and gateway to the database; holds configuration and the tracked entity cache."),
("DbSet&lt;T&gt;","A typed collection representing a database table; source of LINQ queries."),
("UseSqlServer","Extension method (from <code>Microsoft.EntityFrameworkCore.SqlServer</code>) that tells EF Core to generate T-SQL for SQL Server."),
("Convention","A default EF Core rule: a property named <code>Id</code> or <code>&lt;ClassName&gt;Id</code> becomes the PK; <code>string</code> maps to <code>nvarchar(max)</code>."),
("Migration","A generated C# file recording the incremental schema change; applied with <code>dotnet ef database update</code>."),
("ModelSnapshot","EF Core's record of the current model; used to generate the next migration diff."),
("dotnet ef","The EF Core CLI tool (<code>dotnet-ef</code> global tool) for migrations, scaffolding and dbcontext operations."),
("add migration","Computes the diff between ModelSnapshot and the current model and writes <code>Up()</code>/<code>Down()</code> methods."),
("update database","Runs pending migrations against the target database."),
("script migration","Generates an idempotent SQL script — safe to run on a CI server or in a DBA review."),
("Design-time factory","A class implementing <code>IDesignTimeDbContextFactory&lt;TContext&gt;</code> that the CLI uses to build a DbContext when no DI host is available.")],
["Never commit a migration you haven't reviewed — look at the generated C# to confirm EF Core did what you intended.",
"Keep one <code>DbContext</code> per HTTP request (Scoped lifetime) in web apps; never Singleton.",
"<code>dotnet ef migrations remove</code> deletes the last unapplied migration file — only works before <code>update database</code>.",
"Always add <code>MaxLength</code>/<code>Column</code> annotations (or Fluent API) for string properties; <code>nvarchar(max)</code> blocks some indexes.",
"Use <code>dotnet ef migrations script</code> for production deployments rather than <code>update database</code>."],
f'''
<h3>1. NuGet packages and project setup</h3>
{C(r"""
// In StoreData.csproj:
// <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.*" />
// <PackageReference Include="Microsoft.EntityFrameworkCore.Design"    Version="8.0.*">
//   <PrivateAssets>all</PrivateAssets>
//   <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
// </PackageReference>

// Global tool (run once per machine):
// dotnet tool install --global dotnet-ef
""", "StoreData.csproj (excerpt)", lang="xml")}

<h3>2. Model classes</h3>
{C(r"""
// Core/Models/Category.cs
namespace StoreData.Core.Models;

public class Category
{
    public int    CategoryId   { get; set; }         // convention: PK
    public string CategoryName { get; set; } = "";
    public ICollection<Product> Products { get; set; } = [];
}
""", "Core/Models/Category.cs")}
{C(r"""
// Core/Models/Product.cs
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace StoreData.Core.Models;

public class Product
{
    public int    ProductId   { get; set; }

    [Required, MaxLength(200)]
    public string Name        { get; set; } = "";

    [Column(TypeName = "decimal(18,2)")]
    public decimal Price      { get; set; }

    public int    CategoryId  { get; set; }           // FK by convention
    public Category? Category { get; set; }           // navigation
}
""", "Core/Models/Product.cs")}

<h3>3. DbContext</h3>
{C(r"""
using Microsoft.EntityFrameworkCore;
using StoreData.Core.Models;

namespace StoreData.Data;

public class StoreDbContext : DbContext
{
    public StoreDbContext(DbContextOptions<StoreDbContext> options) : base(options) { }

    public DbSet<Category> Categories => Set<Category>();
    public DbSet<Product>  Products   => Set<Product>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        // All Fluent API config goes here (or in IEntityTypeConfiguration classes, Thursday)
        model.Entity<Category>()
             .HasIndex(c => c.CategoryName)
             .IsUnique();
    }
}
""", "Data/StoreDbContext.cs")}

<h3>4. Design-time factory (for the CLI)</h3>
{C(r"""
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace StoreData.Data;

// dotnet ef uses this when there is no running host to provide a DbContext
public class StoreDbContextFactory : IDesignTimeDbContextFactory<StoreDbContext>
{
    public StoreDbContext CreateDbContext(string[] args)
    {
        var options = new DbContextOptionsBuilder<StoreDbContext>()
            .UseSqlServer(
                "Server=localhost,1433;Database=StoreDb;User Id=sa;" +
                "Password=YourStrong!Pass;TrustServerCertificate=True;")
            .Options;
        return new StoreDbContext(options);
    }
}
""", "Data/StoreDbContextFactory.cs")}

<h3>5. First migration and applying it</h3>
{C(r"""
# From the solution root or the project folder containing StoreDbContext:

dotnet ef migrations add InitialCreate --project StoreData --startup-project StoreData
# → Migrations/20261114120000_InitialCreate.cs
# → Migrations/StoreDbContextModelSnapshot.cs

dotnet ef database update --project StoreData
# → Runs InitialCreate.Up() — creates Categories and Products tables

# Review the generated SQL without running it:
dotnet ef migrations script --idempotent --output migrate.sql
""", "Terminal", lang="bash")}

<h3>6. What the generated migration looks like</h3>
{C(r"""
// Auto-generated — review before committing
public partial class InitialCreate : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "Categories",
            columns: table => new
            {
                CategoryId   = table.Column<int>(nullable: false)
                                    .Annotation("SqlServer:Identity", "1, 1"),
                CategoryName = table.Column<string>(maxLength: 200, nullable: false)
            },
            constraints: table => table.PrimaryKey("PK_Categories", x => x.CategoryId));

        migrationBuilder.CreateTable(
            name: "Products",
            columns: table => new
            {
                ProductId  = table.Column<int>(nullable: false)
                                  .Annotation("SqlServer:Identity", "1, 1"),
                Name       = table.Column<string>(maxLength: 200, nullable: false),
                Price      = table.Column<decimal>(type: "decimal(18,2)", nullable: false),
                CategoryId = table.Column<int>(nullable: false)
            },
            constraints: table =>
            {
                table.PrimaryKey("PK_Products", x => x.ProductId);
                table.ForeignKey(
                    name: "FK_Products_Categories_CategoryId",
                    column: x => x.CategoryId,
                    principalTable: "Categories",
                    principalColumn: "CategoryId",
                    onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateIndex("IX_Categories_CategoryName", "Categories", "CategoryName", unique: true);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropTable("Products");
        migrationBuilder.DropTable("Categories");
    }
}
""", "Migrations/InitialCreate.cs (excerpt)")}
{tip("Add a second model change, run <code>dotnet ef migrations add AddStockColumn</code>, review the diff, then <code>dotnet ef database update</code> again — this trains the incremental migration muscle.")}
''',
["Forgetting <code>Microsoft.EntityFrameworkCore.Design</code> — the CLI throws <code>Unable to create a 'DbContext'</code>.",
"Not adding a design-time factory when there is no Web host — same error.",
"Leaving string properties as <code>nvarchar(max)</code> (no <code>[MaxLength]</code>) — blocks some indexes and wastes storage.",
"Running <code>dotnet ef database update</code> in production instead of using <code>script --idempotent</code>.",
"Calling <code>migrations remove</code> after <code>update database</code> — the migration is already applied and the remove will fail."],
("40 min", [
"Create the <code>StoreData</code> class library with the <code>Category</code> and <code>Product</code> models, <code>StoreDbContext</code>, and factory.",
"Run <code>dotnet ef migrations add InitialCreate</code> and inspect the generated file.",
"Apply the migration with <code>dotnet ef database update</code> and confirm the tables exist with <code>sqlcmd</code> or SSMS."]),
[("What is a DbContext?","EF Core's session: it tracks entity state changes, holds the DbSets, translates LINQ to SQL, and manages the connection."),
("Why is a design-time factory needed?","When the CLI runs <code>dotnet ef migrations add</code>, no host is running. The factory gives the CLI a way to build a configured DbContext without startup code."),
("What does <code>migrations remove</code> do?","Deletes the most recent migration file — only safe if it hasn't been applied. After <code>database update</code>, you must revert with a new migration instead.")],
[("Basic","What is EF Core and how does it compare to ADO.NET?","EF Core is an ORM that maps C# classes to database tables and translates LINQ queries to SQL. ADO.NET is the lower-level API you'd write by hand without an ORM. EF Core reduces boilerplate but gives less SQL control."),
("Basic","What is a migration in EF Core?","A C# file with Up() and Down() methods describing a schema change. EF Core generates it from the diff between the last ModelSnapshot and the current model. Apply it with <code>dotnet ef database update</code>."),
("Basic","What conventions does EF Core use for primary keys?","A property named <code>Id</code> or <code>&lt;TypeName&gt;Id</code> becomes the PK automatically. For <code>int</code> and <code>long</code> PKs, SQL Server's IDENTITY is applied."),
("Intermediate","What is the ModelSnapshot and why shouldn't you delete it?","EF Core stores the last-known model in Migrations/&lt;Context&gt;ModelSnapshot.cs. It diffs the current model against this file to generate the next migration. Deleting it means EF Core thinks the schema is empty and regenerates everything."),
("Intermediate","When would you use <code>dotnet ef migrations script --idempotent</code>?","For production. The script wraps each migration in an IF NOT EXISTS check against the __EFMigrationsHistory table, so it's safe to run repeatedly and can be reviewed/approved before execution."),
("Intermediate","How do you configure a decimal column type?","Use the Data Annotation <code>[Column(TypeName = \"decimal(18,2)\")]</code> or Fluent API <code>.HasColumnType(\"decimal(18,2)\")</code>. Without it EF Core maps C# decimal to SQL Server's <code>decimal(18,2)</code> by default in EF 8, but it is best to be explicit.")])

# ================= DAY 4  THU =================
d4 = day(4, "THU", "EF Core relationships: Fluent API and IEntityTypeConfiguration",
"Map one-to-many and many-to-many relationships correctly, control cascade behaviour, and move configuration out of OnModelCreating into clean per-type classes.",
[("Navigation property","A C# property pointing to a related entity or collection; EF Core uses it to build JOINs."),
("Foreign key","A scalar property (e.g. <code>CategoryId</code>) that holds the PK value of the related entity."),
("One-to-many","One Category has many Products; the FK lives on the many-side (Products.CategoryId)."),
("Many-to-many","Order ↔ Product; EF Core 5+ creates a join table automatically via skip navigations."),
("Skip navigation","A direct collection on each end of a many-to-many without an explicit join entity."),
("Join entity","An explicit class (e.g. <code>OrderLine</code>) for a many-to-many when you need extra columns on the join row."),
("Required relationship","FK is non-nullable; deleting the principal cascades to dependents by convention."),
("Optional relationship","FK is nullable; delete of principal sets FK to NULL by convention."),
("Cascade delete","SQL Server and EF Core automatically delete dependent rows when the principal is deleted."),
("Fluent API","Calls to <code>modelBuilder.Entity&lt;T&gt;()</code> in <code>OnModelCreating</code> that override conventions."),
("IEntityTypeConfiguration&lt;T&gt;","Interface for a per-entity configuration class; keeps <code>OnModelCreating</code> clean."),
("HasOne/HasMany/WithMany/WithOne","Fluent API methods that fully describe a relationship.")],
["Naming conventions handle most simple FKs. Use Fluent API when names deviate or you need extra control.",
"<code>DeleteBehavior.Restrict</code> prevents accidental cascade delete; prefer it for most business entities.",
"Skip navigations are the cleanest many-to-many when the join row has no extra columns.",
"Always put a unique index on the join table's composite PK — EF Core does this by convention.",
"Use <code>IEntityTypeConfiguration&lt;T&gt;</code> classes for each entity to keep <code>OnModelCreating</code> from growing uncontrollably."],
f'''
<h3>1. One-to-many (Category → Products, full example)</h3>
{C(r"""
// All Fluent API config in one place per entity
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using StoreData.Core.Models;

namespace StoreData.Data.Config;

public class ProductConfig : IEntityTypeConfiguration<Product>
{
    public void Configure(EntityTypeBuilder<Product> b)
    {
        b.ToTable("Products");
        b.HasKey(p => p.ProductId);

        b.Property(p => p.Name)
         .IsRequired()
         .HasMaxLength(200);

        b.Property(p => p.Price)
         .HasColumnType("decimal(18,2)");

        // One Category has many Products; FK is ProductId (nullable = false)
        b.HasOne(p => p.Category)
         .WithMany(c => c.Products)
         .HasForeignKey(p => p.CategoryId)
         .OnDelete(DeleteBehavior.Restrict);  // prevent accidental cascade
    }
}
""", "Data/Config/ProductConfig.cs")}
{C(r"""
// Register all IEntityTypeConfiguration classes with one line in OnModelCreating:
protected override void OnModelCreating(ModelBuilder model)
{
    model.ApplyConfigurationsFromAssembly(typeof(StoreDbContext).Assembly);
}
""", "Data/StoreDbContext.cs (OnModelCreating)")}

<h3>2. Many-to-many via skip navigations (Order ↔ Product)</h3>
{C(r"""
// Minimal model — no explicit join entity needed
public class Order
{
    public int    OrderId     { get; set; }
    public string CustomerName { get; set; } = "";
    public ICollection<Product> Products { get; set; } = [];
}

// Product already has: public ICollection<Order> Orders { get; set; } = [];
""", "Core/Models/Order.cs")}
{C(r"""
public class OrderConfig : IEntityTypeConfiguration<Order>
{
    public void Configure(EntityTypeBuilder<Order> b)
    {
        b.ToTable("Orders");
        b.HasKey(o => o.OrderId);

        b.Property(o => o.CustomerName).IsRequired().HasMaxLength(200);

        // EF Core creates the join table OrderProduct automatically
        b.HasMany(o => o.Products)
         .WithMany(p => p.Orders)
         .UsingEntity(j => j.ToTable("OrderProducts"));
    }
}
""", "Data/Config/OrderConfig.cs")}

<h3>3. Many-to-many with an explicit join entity (OrderLine)</h3>
{C(r"""
// Use when the join row has extra columns (Qty, UnitPrice, Discount)
public class OrderLine
{
    public int     OrderId   { get; set; }     // composite PK part 1
    public int     ProductId { get; set; }     // composite PK part 2
    public int     Qty       { get; set; }
    public decimal UnitPrice { get; set; }

    public Order?   Order   { get; set; }
    public Product? Product { get; set; }
}
""", "Core/Models/OrderLine.cs")}
{C(r"""
public class OrderLineConfig : IEntityTypeConfiguration<OrderLine>
{
    public void Configure(EntityTypeBuilder<OrderLine> b)
    {
        b.ToTable("OrderLines");
        b.HasKey(ol => new { ol.OrderId, ol.ProductId });   // composite PK

        b.Property(ol => ol.UnitPrice).HasColumnType("decimal(18,2)");

        b.HasOne(ol => ol.Order)
         .WithMany()
         .HasForeignKey(ol => ol.OrderId)
         .OnDelete(DeleteBehavior.Cascade);

        b.HasOne(ol => ol.Product)
         .WithMany()
         .HasForeignKey(ol => ol.ProductId)
         .OnDelete(DeleteBehavior.Restrict);
    }
}
""", "Data/Config/OrderLineConfig.cs")}

<h3>4. Required vs optional relationships</h3>
{table(["","Required","Optional"],[
["FK type","<code>int CategoryId</code> (non-nullable)","<code>int? SupplierId</code> (nullable)"],
["Default cascade","<code>Cascade</code> — delete principal deletes dependents","<code>ClientSetNull</code> — EF sets FK to null"],
["SQL Server FK","<code>ON DELETE CASCADE</code>","<code>ON DELETE SET NULL</code> or <code>NO ACTION</code>"],
["Use when","Dependent can't exist without principal","Dependent can exist without the principal"]])}

<h3>5. Data annotations vs Fluent API</h3>
{table(["Capability","Data Annotations","Fluent API"],[
["PK, MaxLength, Required","<code>[Key]</code> <code>[MaxLength]</code> <code>[Required]</code>","<code>HasKey</code> <code>HasMaxLength</code> <code>IsRequired</code>"],
["Composite PK","Not supported","<code>HasKey(e =&gt; new {{ e.A, e.B }})</code>"],
["Relationship details","<code>[ForeignKey]</code> (limited)","<code>HasOne/HasMany/WithMany</code>"],
["Cascade behaviour","Not supported","<code>OnDelete(DeleteBehavior.xxx)</code>"],
["Owned entity","Not supported","<code>OwnsOne/OwnsMany</code>"],
["Table splitting","Not supported","<code>ToTable</code> with <code>ToView</code>"],
["Location","On the model class","Separate config class / OnModelCreating"],
["Recommendation","Simple constraints on POCOs","Anything advanced or when model must stay clean"]])}

<h3>6. Adding migrations for the new entities</h3>
{C(r"""
# After adding Order, OrderLine and their configs:
dotnet ef migrations add AddOrdersAndLines
dotnet ef database update

# Check the generated SQL to verify composite PK and FKs look right:
dotnet ef migrations script --idempotent
""", "Terminal", lang="bash")}
{tip("Run <code>dotnet ef migrations script</code> after every migration and skim the output for unexpected DROP TABLE statements — EF Core occasionally gets confused and tries to recreate an existing table if the ModelSnapshot diverges.")}
''',
["Forgetting to add the navigation property on both sides and wondering why the FK column isn't created.",
"Using <code>DeleteBehavior.Cascade</code> on a many-to-many join table principal — can delete products from an order, usually not intended.",
"Declaring a composite PK with an annotation (<code>[Key]</code> on two properties) — only Fluent API supports composite PKs.",
"Not calling <code>ApplyConfigurationsFromAssembly</code> and wondering why the config class has no effect.",
"Mixing annotations and Fluent API for the same property — Fluent API wins but it's confusing."],
("40 min", [
"Add a <code>Supplier</code> entity with an optional relationship to <code>Product</code> (nullable <code>SupplierId</code>). Generate and apply the migration.",
"Add an <code>OrderLine</code> join entity with a composite PK and <code>UnitPrice</code>/<code>Qty</code> columns. Write the <code>IEntityTypeConfiguration</code> class.",
"Query all orders with their lines and products loaded using <code>Include</code>/<code>ThenInclude</code>."]),
[("What is a skip navigation?","A collection property on each end of a many-to-many that bypasses the join entity class, letting you write <code>order.Products.Add(p)</code> without touching the join table directly."),
("What does <code>ApplyConfigurationsFromAssembly</code> do?","Scans the assembly for classes implementing <code>IEntityTypeConfiguration&lt;T&gt;</code> and calls <code>Configure</code> on each — no manual registration needed."),
("What is the difference between Cascade and Restrict delete behaviour?","Cascade: deleting the principal deletes all dependents automatically. Restrict: deleting the principal throws if dependents exist — you must delete them first.")],
[("Basic","How does EF Core know which property is the foreign key?","By convention: a property named <code>&lt;NavigationName&gt;Id</code> (e.g. <code>CategoryId</code>) becomes the FK for the <code>Category</code> navigation. Use <code>[ForeignKey]</code> or <code>HasForeignKey</code> when the name deviates."),
("Basic","What is a navigation property?","A C# property that references a related entity or collection. EF Core uses it to generate JOINs and load related data with Include."),
("Intermediate","When should you use an explicit join entity vs skip navigations?","Use an explicit join entity (like OrderLine) when the join row has extra data (Qty, UnitPrice). Use skip navigations for a pure relationship with no extra columns."),
("Intermediate","What does IEntityTypeConfiguration&lt;T&gt; do?","Moves per-entity Fluent API configuration to its own class, keeping OnModelCreating clean. Registered via model.ApplyConfigurationsFromAssembly."),
("Intermediate","What is the difference between required and optional relationships in EF Core?","Required: FK is non-nullable; default cascade is Cascade. Optional: FK is nullable; default cascade is ClientSetNull (EF sets the FK to null in memory before saving)."),
("Intermediate","Why is Restrict safer than Cascade for business data?","Cascade deletes silently remove child rows. Restrict forces you to explicitly decide what to do with dependents, preventing accidental data loss.")])

# ================= DAY 5  FRI =================
d5 = day(5, "FRI", "CRUD with EF Core and change tracking",
"Add, query, update and delete entities, understand how change tracking states work, and see how SaveChanges builds the SQL behind the scenes.",
[("Change tracking","EF Core watches every entity it fetched and computes what changed when SaveChanges is called."),
("EntityState","Enum: Added, Modified, Deleted, Unchanged, Detached — the state of an entity in the DbContext."),
("Snapshot","A deep copy EF Core takes when it loads an entity; it diffs the current values against this on SaveChanges."),
("Add","<code>context.Products.Add(p)</code> — marks entity as Added; EF Core will INSERT on SaveChanges."),
("Update","<code>context.Products.Update(p)</code> — marks all scalar properties as Modified; EF Core will UPDATE on SaveChanges."),
("Remove","<code>context.Products.Remove(p)</code> — marks entity as Deleted; EF Core will DELETE on SaveChanges."),
("SaveChanges","Wraps all pending changes in a transaction and executes the SQL; returns rows affected."),
("No-tracking query","<code>.AsNoTracking()</code> — EF Core skips the snapshot overhead; use for read-only queries."),
("Entry","<code>context.Entry(entity).State</code> — inspect or manually set the EntityState."),
("Detached","Entity not tracked by any context; obtained from a no-tracking query or created with <code>new</code>."),
("Concurrency token","A <code>[Timestamp]</code>/<code>rowversion</code> column; EF Core adds <code>WHERE RowVersion = @orig</code> to UPDATE/DELETE.")],
["Use <code>AsNoTracking()</code> for every read-only query — it can be 2–5× faster at scale.",
"<code>context.Update(entity)</code> marks ALL columns as modified; prefer fetching first and changing only the properties that changed.",
"<code>context.SaveChanges()</code> wraps all changes in a single implicit transaction.",
"Multiple <code>Add</code> calls followed by one <code>SaveChanges</code> is a single transaction; this is the unit-of-work pattern.",
"Always call <code>SaveChangesAsync</code> in async code."],
f'''
<h3>1. Create (Add + SaveChanges)</h3>
{C(r"""
await using var db = new StoreDbContext(options);

var category = new Category { CategoryName = "Electronics" };
db.Categories.Add(category);
await db.SaveChangesAsync();
// EF Core generated: INSERT INTO Categories (CategoryName) VALUES (N'Electronics')
// IDENTITY flows back automatically — category.CategoryId is now populated

var product = new Product { Name = "Noise Cancelling Headphones", Price = 4999m, CategoryId = category.CategoryId };
db.Products.Add(product);
await db.SaveChangesAsync();
Console.WriteLine($"New product id: {product.ProductId}");
""", "EfCreate.cs")}

<h3>2. Read — LINQ queries and AsNoTracking</h3>
{C(r"""
await using var db = new StoreDbContext(options);

// All products (no tracking for read-only display)
List<Product> all = await db.Products
    .AsNoTracking()
    .OrderBy(p => p.Price)
    .ToListAsync();

// Filter + include navigation
List<Product> expensive = await db.Products
    .AsNoTracking()
    .Include(p => p.Category)
    .Where(p => p.Price > 1000m)
    .OrderByDescending(p => p.Price)
    .ToListAsync();

foreach (var p in expensive)
    Console.WriteLine($"  [{p.Category?.CategoryName}] {p.Name}  ₹{p.Price:N2}");

// Single row (throws if more than one)
Product? found = await db.Products
    .AsNoTracking()
    .FirstOrDefaultAsync(p => p.ProductId == 7);
""", "EfRead.cs")}
{tip("EF Core translates LINQ to SQL server-side. Add <code>.LogTo(Console.WriteLine)</code> to <code>DbContextOptionsBuilder</code> (Saturday) to see the generated T-SQL.")}

<h3>3. Update — fetch-and-modify vs context.Update</h3>
{C(r"""
await using var db = new StoreDbContext(options);

// ✓ Preferred: fetch, change only the properties you want to update
var product = await db.Products.FindAsync(7);
if (product is not null)
{
    product.Price = 3499m;                       // only Price is marked Modified
    await db.SaveChangesAsync();
    // UPDATE Products SET Price = 3499 WHERE ProductId = 7
}

// ⚠ context.Update — marks EVERY column as Modified (complete overwrite risk)
var detached = new Product { ProductId = 7, Name = "Headphones", Price = 3499m, CategoryId = 1 };
db.Products.Update(detached);    // all columns in the UPDATE; Name/CategoryId must be correct
await db.SaveChangesAsync();
""", "EfUpdate.cs")}

<h3>4. Delete</h3>
{C(r"""
await using var db = new StoreDbContext(options);

// Fetch and remove
var toDelete = await db.Products.FindAsync(7);
if (toDelete is not null)
{
    db.Products.Remove(toDelete);
    await db.SaveChangesAsync();
    // DELETE FROM Products WHERE ProductId = 7
}

// Stub delete — no SELECT round trip needed (EF Core 7+ ExecuteDeleteAsync is cleaner)
// db.Products.Remove(new Product { ProductId = 7 });  // Attach + mark Deleted
// await db.SaveChangesAsync();

// EF Core 7+ bulk delete (no change tracking overhead):
await db.Products.Where(p => p.Price < 10m).ExecuteDeleteAsync();
""", "EfDelete.cs")}

<h3>5. How SaveChanges builds SQL</h3>
<ol>
<li>EF Core iterates every tracked entity and compares current values with the snapshot.</li>
<li>It groups changes into INSERT / UPDATE / DELETE commands.</li>
<li>It wraps them in an implicit <code>BEGIN TRANSACTION</code> … <code>COMMIT</code>.</li>
<li>For IDENTITY PKs it appends <code>OUTPUT INSERTED.[Id]</code> so the C# object gets the generated key back.</li>
</ol>
{C(r"""
await using var db = new StoreDbContext(options);

// All three DML statements in ONE transaction
var cat = new Category { CategoryName = "Accessories" };
db.Categories.Add(cat);

var obsolete = await db.Products.FindAsync(3);
if (obsolete is not null) db.Products.Remove(obsolete);

var existing = await db.Products.FindAsync(5);
if (existing is not null) existing.Price *= 0.9m;      // 10 % discount

int changes = await db.SaveChangesAsync();              // commit: INSERT + DELETE + UPDATE
Console.WriteLine($"{changes} change(s) saved");
""", "SaveChangesDemo.cs")}

<h3>6. EntityState inspection</h3>
{C(r"""
await using var db = new StoreDbContext(options);

var p = new Product { Name = "Test", Price = 1m, CategoryId = 1 };
Console.WriteLine(db.Entry(p).State);     // Detached — not tracked yet

db.Products.Add(p);
Console.WriteLine(db.Entry(p).State);     // Added

await db.SaveChangesAsync();
Console.WriteLine(db.Entry(p).State);     // Unchanged

p.Price = 2m;
Console.WriteLine(db.Entry(p).State);     // Modified (detected on property set via snapshot)

db.Products.Remove(p);
Console.WriteLine(db.Entry(p).State);     // Deleted
""", "EntityStates.cs")}
''',
["Calling <code>context.Update(entity)</code> with a detached entity that's missing some properties — overwrites columns with default values.",
"Forgetting <code>await</code> before <code>SaveChangesAsync</code> — no data is saved, no exception, just silence.",
"Using the same DbContext instance for two parallel async operations — DbContext is not thread-safe.",
"Not using <code>AsNoTracking</code> in a report endpoint that returns thousands of rows — wastes memory on snapshots.",
"Modifying a property after <code>SaveChanges</code> and expecting EF to auto-save — you must call <code>SaveChanges</code> again."],
("40 min", [
"Write a console menu: (1) List products, (2) Add product, (3) Update price, (4) Delete product, (Q) Quit. Each option calls the matching EF Core CRUD operation.",
"Print the generated SQL by setting <code>.LogTo(Console.WriteLine)</code> on the DbContextOptionsBuilder and inspect the INSERT/UPDATE/DELETE statements.",
"Change the update to use <code>context.Products.Update(detached)</code> and observe that all columns appear in the UPDATE — confirm with the log."]),
[("What is an EntityState?","An enum value (Added, Modified, Deleted, Unchanged, Detached) that tells EF Core what SQL to generate for each tracked entity on SaveChanges."),
("Why prefer AsNoTracking for read-only queries?","EF Core takes a snapshot of each loaded entity for change detection. Skipping tracking means no snapshots, less memory, and faster queries."),
("How does EF Core get the generated IDENTITY value back?","It appends <code>OUTPUT INSERTED.[PK]</code> to the INSERT statement. The returned value is applied to the entity's key property automatically.")],
[("Basic","What does SaveChanges do?","It detects all changes in tracked entities (compare vs snapshot), generates the minimum required INSERT/UPDATE/DELETE statements, wraps them in a transaction, executes them, and applies generated PKs back to entities."),
("Basic","What is AsNoTracking?","A LINQ operator that tells EF Core not to track the returned entities. Useful for read-only queries — no snapshot overhead, faster and lighter."),
("Basic","How do you delete an entity with EF Core?","Load it (or attach it by PK), call <code>db.Remove(entity)</code>, then <code>db.SaveChangesAsync()</code>. For bulk deletes without loading, use <code>.ExecuteDeleteAsync()</code> (EF Core 7+)."),
("Intermediate","What is the difference between context.Add(entity) and context.Update(entity)?","Add marks the entity as Added (INSERT). Update marks it as Modified with ALL scalar properties included in the UPDATE — risky with detached objects because properties you didn't set become their default values in the database."),
("Intermediate","How does change tracking detect modifications?","At load time EF Core takes a snapshot of the entity's property values. On SaveChanges, it compares current values to the snapshot. Any difference marks that property (and the entity) as Modified."),
("Intermediate","What is a concurrency token and when do you need one?","A <code>[Timestamp]</code> (rowversion) column that EF Core adds to WHERE clauses in UPDATE/DELETE. If another process changed the row, the WHERE clause finds zero rows, EF throws <code>DbUpdateConcurrencyException</code>. Use it when optimistic concurrency control matters.")])

# ================= DAY 6  SAT =================
d6 = day(6, "SAT", "StoreData.sln — ADO.NET, Dapper and EF Core side by side",
"Build a single console application with three interchangeable data-access layers behind one interface, backed by SQL Server in Docker.",
[("ICatalogDal","The shared interface: GetAll, GetById, Insert, Update, Delete for products."),
("AdoCatalogDal","Implements ICatalogDal with raw <code>Microsoft.Data.SqlClient</code>."),
("DapperCatalogDal","Implements ICatalogDal with Dapper."),
("EfCatalogDal","Implements ICatalogDal with EF Core DbContext."),
("DAL","Data Access Layer — the code responsible for reading and writing to the database.")],
["All three DALs implement the same interface so the console menu can swap between them at runtime.",
"The Product and Category models are shared in a Core class library.",
"<code>docker compose up</code> starts SQL Server; <code>sqlcmd</code> creates the schema."],
f'''
<h3>Solution layout</h3>
{C(r"""
StoreData.sln
├── StoreData.Core/      (class library — models, interface)
│   ├── Models/
│   │   ├── Category.cs
│   │   └── Product.cs
│   └── ICatalogDal.cs
├── StoreData.Data/      (class library — three DAL implementations + EF migrations)
│   ├── Ado/
│   │   └── AdoCatalogDal.cs
│   ├── Dapper/
│   │   └── DapperCatalogDal.cs
│   ├── Ef/
│   │   ├── StoreDbContext.cs
│   │   ├── StoreDbContextFactory.cs
│   │   ├── Config/
│   │   │   ├── ProductConfig.cs
│   │   │   └── CategoryConfig.cs
│   │   ├── EfCatalogDal.cs
│   │   └── Migrations/
└── StoreData.App/       (console project)
    └── Program.cs
""", "Solution structure", lang="text")}

<h3>Step 1 — scaffold and add packages</h3>
{C(r"""
dotnet new sln -n StoreData
dotnet new classlib -n StoreData.Core
dotnet new classlib -n StoreData.Data
dotnet new console  -n StoreData.App

dotnet sln add StoreData.Core StoreData.Data StoreData.App
dotnet add StoreData.Data reference StoreData.Core
dotnet add StoreData.App  reference StoreData.Core
dotnet add StoreData.App  reference StoreData.Data

dotnet add StoreData.Data package Microsoft.Data.SqlClient
dotnet add StoreData.Data package Dapper
dotnet add StoreData.Data package Microsoft.EntityFrameworkCore.SqlServer
dotnet add StoreData.Data package Microsoft.EntityFrameworkCore.Design
dotnet tool install --global dotnet-ef
""", "Terminal", lang="bash")}

<h3>Step 2 — Docker + schema setup</h3>
{C(r"""
# docker-compose.yml (place in solution root)
version: "3.9"
services:
  sql:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      SA_PASSWORD: "YourStrong!Pass"
      ACCEPT_EULA: "Y"
    ports:
      - "1433:1433"
""", "docker-compose.yml", lang="yaml")}
{C(r"""
# Start, then create schema:
docker compose up -d
sleep 10   # wait for SQL Server to be ready

docker exec -it storedata-sql-1 /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "YourStrong!Pass" -No -Q "
CREATE DATABASE StoreDb;
GO
USE StoreDb;
GO
CREATE TABLE Categories (
    CategoryId   INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(200) NOT NULL UNIQUE
);
CREATE TABLE Products (
    ProductId  INT IDENTITY(1,1) PRIMARY KEY,
    Name       NVARCHAR(200)   NOT NULL,
    Price      DECIMAL(18,2)   NOT NULL,
    CategoryId INT             NOT NULL REFERENCES Categories(CategoryId)
);
INSERT INTO Categories (CategoryName) VALUES ('Electronics'), ('Accessories'), ('Books');
INSERT INTO Products (Name, Price, CategoryId) VALUES
  ('Wireless Mouse',    799.00, 2),
  ('Mechanical Keyboard', 2499.00, 2),
  ('Clean Code (book)', 499.00, 3),
  ('Noise Cancelling Headphones', 4999.00, 1),
  ('USB-C Hub',         1299.00, 2);
"
""", "setup.sh", lang="bash")}

<h3>Step 3 — Core models and interface</h3>
{C(r"""
namespace StoreData.Core.Models;

public class Product
{
    public int     ProductId   { get; set; }
    public string  Name        { get; set; } = "";
    public decimal Price       { get; set; }
    public int     CategoryId  { get; set; }
    public string  CategoryName { get; set; } = "";   // read-only join field
}
""", "StoreData.Core/Models/Product.cs")}
{C(r"""
using StoreData.Core.Models;

namespace StoreData.Core;

public interface ICatalogDal
{
    Task<IReadOnlyList<Product>> GetAllAsync();
    Task<Product?>               GetByIdAsync(int id);
    Task<int>                    InsertAsync(string name, decimal price, int categoryId);
    Task<bool>                   UpdatePriceAsync(int id, decimal newPrice);
    Task<bool>                   DeleteAsync(int id);
}
""", "StoreData.Core/ICatalogDal.cs")}

<h3>Step 4 — AdoCatalogDal</h3>
{C(r"""
using System.Data;
using Microsoft.Data.SqlClient;
using StoreData.Core;
using StoreData.Core.Models;

namespace StoreData.Data.Ado;

public class AdoCatalogDal(string connStr) : ICatalogDal
{
    public async Task<IReadOnlyList<Product>> GetAllAsync()
    {
        const string sql = @"
            SELECT p.ProductId, p.Name, p.Price, p.CategoryId, c.CategoryName
            FROM   Products p JOIN Categories c ON c.CategoryId = p.CategoryId
            ORDER  BY p.Name";

        var list = new List<Product>();
        await using var conn = new SqlConnection(connStr);
        await conn.OpenAsync();
        await using var cmd  = new SqlCommand(sql, conn);
        await using var reader = await cmd.ExecuteReaderAsync();
        while (await reader.ReadAsync())
            list.Add(Map(reader));
        return list;
    }

    public async Task<Product?> GetByIdAsync(int id)
    {
        const string sql = @"
            SELECT p.ProductId, p.Name, p.Price, p.CategoryId, c.CategoryName
            FROM   Products p JOIN Categories c ON c.CategoryId = p.CategoryId
            WHERE  p.ProductId = @id";
        await using var conn = new SqlConnection(connStr);
        await conn.OpenAsync();
        await using var cmd = new SqlCommand(sql, conn);
        cmd.Parameters.Add("@id", SqlDbType.Int).Value = id;
        await using var reader = await cmd.ExecuteReaderAsync(CommandBehavior.SingleRow);
        return await reader.ReadAsync() ? Map(reader) : null;
    }

    public async Task<int> InsertAsync(string name, decimal price, int categoryId)
    {
        const string sql = @"
            INSERT INTO Products (Name, Price, CategoryId)
            OUTPUT INSERTED.ProductId
            VALUES (@n, @p, @c)";
        await using var conn = new SqlConnection(connStr);
        await conn.OpenAsync();
        await using var cmd = new SqlCommand(sql, conn);
        cmd.Parameters.Add("@n", SqlDbType.NVarChar, 200).Value = name;
        cmd.Parameters.Add("@p", SqlDbType.Decimal).Value        = price;
        cmd.Parameters.Add("@c", SqlDbType.Int).Value            = categoryId;
        return Convert.ToInt32(await cmd.ExecuteScalarAsync());
    }

    public async Task<bool> UpdatePriceAsync(int id, decimal newPrice)
    {
        await using var conn = new SqlConnection(connStr);
        await conn.OpenAsync();
        await using var cmd = new SqlCommand(
            "UPDATE Products SET Price = @p WHERE ProductId = @id", conn);
        cmd.Parameters.Add("@p",  SqlDbType.Decimal).Value = newPrice;
        cmd.Parameters.Add("@id", SqlDbType.Int).Value     = id;
        return await cmd.ExecuteNonQueryAsync() == 1;
    }

    public async Task<bool> DeleteAsync(int id)
    {
        await using var conn = new SqlConnection(connStr);
        await conn.OpenAsync();
        await using var cmd = new SqlCommand(
            "DELETE FROM Products WHERE ProductId = @id", conn);
        cmd.Parameters.Add("@id", SqlDbType.Int).Value = id;
        return await cmd.ExecuteNonQueryAsync() == 1;
    }

    private static Product Map(SqlDataReader r) => new()
    {
        ProductId    = r.GetInt32(0),
        Name         = r.GetString(1),
        Price        = r.GetDecimal(2),
        CategoryId   = r.GetInt32(3),
        CategoryName = r.GetString(4),
    };
}
""", "StoreData.Data/Ado/AdoCatalogDal.cs")}

<h3>Step 5 — DapperCatalogDal</h3>
{C(r"""
using Dapper;
using Microsoft.Data.SqlClient;
using StoreData.Core;
using StoreData.Core.Models;

namespace StoreData.Data.Dapper;

public class DapperCatalogDal(string connStr) : ICatalogDal
{
    private const string JoinSql = @"
        SELECT p.ProductId, p.Name, p.Price, p.CategoryId, c.CategoryName
        FROM   Products p JOIN Categories c ON c.CategoryId = p.CategoryId";

    public async Task<IReadOnlyList<Product>> GetAllAsync()
    {
        await using var conn = new SqlConnection(connStr);
        return (await conn.QueryAsync<Product>(JoinSql + " ORDER BY p.Name")).ToList();
    }

    public async Task<Product?> GetByIdAsync(int id)
    {
        await using var conn = new SqlConnection(connStr);
        return await conn.QueryFirstOrDefaultAsync<Product>(
            JoinSql + " WHERE p.ProductId = @id", new { id });
    }

    public async Task<int> InsertAsync(string name, decimal price, int categoryId)
    {
        await using var conn = new SqlConnection(connStr);
        return await conn.ExecuteScalarAsync<int>(
            "INSERT INTO Products (Name,Price,CategoryId) OUTPUT INSERTED.ProductId VALUES (@name,@price,@categoryId)",
            new { name, price, categoryId });
    }

    public async Task<bool> UpdatePriceAsync(int id, decimal newPrice)
    {
        await using var conn = new SqlConnection(connStr);
        int rows = await conn.ExecuteAsync(
            "UPDATE Products SET Price = @newPrice WHERE ProductId = @id", new { newPrice, id });
        return rows == 1;
    }

    public async Task<bool> DeleteAsync(int id)
    {
        await using var conn = new SqlConnection(connStr);
        return await conn.ExecuteAsync("DELETE FROM Products WHERE ProductId = @id", new { id }) == 1;
    }
}
""", "StoreData.Data/Dapper/DapperCatalogDal.cs")}

<h3>Step 6 — EfCatalogDal</h3>
{C(r"""
using Microsoft.EntityFrameworkCore;
using StoreData.Core;
using StoreData.Core.Models;
using StoreData.Data.Ef;

namespace StoreData.Data.Ef;

public class EfCatalogDal(StoreDbContext db) : ICatalogDal
{
    public async Task<IReadOnlyList<Product>> GetAllAsync() =>
        await db.Products
                .AsNoTracking()
                .Include(p => p.Category)
                .OrderBy(p => p.Name)
                .Select(p => new Product
                {
                    ProductId    = p.ProductId,
                    Name         = p.Name,
                    Price        = p.Price,
                    CategoryId   = p.CategoryId,
                    CategoryName = p.Category!.CategoryName
                })
                .ToListAsync();

    public async Task<Product?> GetByIdAsync(int id) =>
        await db.Products
                .AsNoTracking()
                .Include(p => p.Category)
                .Where(p => p.ProductId == id)
                .Select(p => new Product
                {
                    ProductId    = p.ProductId,
                    Name         = p.Name,
                    Price        = p.Price,
                    CategoryId   = p.CategoryId,
                    CategoryName = p.Category!.CategoryName
                })
                .FirstOrDefaultAsync();

    public async Task<int> InsertAsync(string name, decimal price, int categoryId)
    {
        var product = new StoreData.Core.Models.EfProduct
            { Name = name, Price = price, CategoryId = categoryId };
        db.Products.Add(product);
        await db.SaveChangesAsync();
        return product.ProductId;
    }

    public async Task<bool> UpdatePriceAsync(int id, decimal newPrice)
    {
        var product = await db.Products.FindAsync(id);
        if (product is null) return false;
        product.Price = newPrice;
        await db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> DeleteAsync(int id)
    {
        int rows = await db.Products.Where(p => p.ProductId == id).ExecuteDeleteAsync();
        return rows == 1;
    }
}
""", "StoreData.Data/Ef/EfCatalogDal.cs")}

<h3>Step 7 — Console menu (Program.cs)</h3>
{C(r"""
using Microsoft.EntityFrameworkCore;
using StoreData.Core;
using StoreData.Data.Ado;
using StoreData.Data.Dapper;
using StoreData.Data.Ef;

const string ConnStr =
    "Server=localhost,1433;Database=StoreDb;User Id=sa;" +
    "Password=YourStrong!Pass;TrustServerCertificate=True;";

// Switch between DALs here (or via config)
ICatalogDal dal = ChooseDal("ado");   // "ado" | "dapper" | "ef"

await RunMenuAsync(dal);

static ICatalogDal ChooseDal(string name)
{
    const string cs = "Server=localhost,1433;Database=StoreDb;User Id=sa;" +
                      "Password=YourStrong!Pass;TrustServerCertificate=True;";
    return name switch
    {
        "dapper" => new DapperCatalogDal(cs),
        "ef"     => new EfCatalogDal(BuildDb(cs)),
        _        => new AdoCatalogDal(cs)       // "ado" is default
    };
}

static StoreDbContext BuildDb(string cs)
{
    var opts = new DbContextOptionsBuilder<StoreDbContext>()
        .UseSqlServer(cs)
        .LogTo(Console.WriteLine, Microsoft.Extensions.Logging.LogLevel.Information)
        .Options;
    return new StoreDbContext(opts);
}

async Task RunMenuAsync(ICatalogDal dal)
{
    while (true)
    {
        Console.WriteLine("\n1) List products  2) Get by id  3) Insert  4) Update price  5) Delete  Q) Quit");
        Console.Write("Choice: ");
        switch (Console.ReadLine()?.Trim().ToUpper())
        {
            case "1":
                foreach (var p in await dal.GetAllAsync())
                    Console.WriteLine($"  {p.ProductId,3}  {p.Name,-35}  [{p.CategoryName}]  ₹{p.Price:N2}");
                break;
            case "2":
                Console.Write("Id: ");
                if (int.TryParse(Console.ReadLine(), out int id))
                {
                    var p = await dal.GetByIdAsync(id);
                    Console.WriteLine(p is null ? "  Not found" : $"  {p.Name}  ₹{p.Price:N2}");
                }
                break;
            case "3":
                Console.Write("Name: ");   string name = Console.ReadLine()!;
                Console.Write("Price: ");  decimal price = decimal.Parse(Console.ReadLine()!);
                Console.Write("CategoryId: "); int cat = int.Parse(Console.ReadLine()!);
                int newId = await dal.InsertAsync(name, price, cat);
                Console.WriteLine($"  Inserted with id {newId}");
                break;
            case "4":
                Console.Write("Id: ");    int uid = int.Parse(Console.ReadLine()!);
                Console.Write("New price: "); decimal np = decimal.Parse(Console.ReadLine()!);
                Console.WriteLine(await dal.UpdatePriceAsync(uid, np) ? "  Updated" : "  Not found");
                break;
            case "5":
                Console.Write("Id: ");    int did = int.Parse(Console.ReadLine()!);
                Console.WriteLine(await dal.DeleteAsync(did) ? "  Deleted" : "  Not found");
                break;
            case "Q":
                return;
        }
    }
}
""", "StoreData.App/Program.cs")}

<h3>Expected output (DAL = ado)</h3>
{C(r"""
1) List products  2) Get by id  3) Insert  4) Update price  5) Delete  Q) Quit
Choice: 1
    1  Clean Code (book)                  [Books]       ₹499.00
    4  Mechanical Keyboard                [Accessories] ₹2,499.00
    5  Noise Cancelling Headphones        [Electronics] ₹4,999.00
    3  USB-C Hub                          [Accessories] ₹1,299.00
    2  Wireless Mouse                     [Accessories] ₹799.00
""", lang="text")}

<h3>Stretch goals</h3>
{ul(["Switch the DAL at runtime by reading the first CLI argument: <code>dotnet run -- dapper</code>.",
"Add a <code>GetByCategoryAsync(string name)</code> method to the interface and implement it in all three layers.",
"Add a <code>Category</code> CRUD menu option — test that FK violation is caught properly when deleting a category with products."])}
''',
iqs=[("Basic","What is the purpose of the ICatalogDal interface?","It decouples the console menu from the data-access implementation. Any class that satisfies the contract can be swapped in without changing the calling code — the same pattern used in Weeks 2 and 4 with IRepository."),
("Basic","Why do all three DALs take a connection string or DbContext in the constructor?","To support dependency injection. The caller (console or later a web controller) supplies the dependency; the DAL doesn't create it."),
("Intermediate","How would you test the three DALs for consistency?","Write a parameterised test fixture (xUnit IClassFixture + MemberData) that runs the same CRUD assertions against all three implementations, using a Localdb or Docker container as the test database."),
("Intermediate","What would you change if the application grew to hundreds of concurrent users?","Use DbContextFactory for EF (avoid a Singleton DbContext), ensure all connection opens/closes return quickly to the pool, add indexes for query columns, consider Dapper for heavy read paths, and move to an async service layer.")])

# ================= DAY 7  SUN =================
d7 = day(7, "SUN", "Compare, test to break, README, git and week revision",
"Bench the three DALs, test their edge cases, write the README, commit, and lock in the week's concepts before Week 16.",
[("Stopwatch","<code>System.Diagnostics.Stopwatch</code> measures elapsed wall-clock time for simple micro-benchmarks."),
("LogTo","<code>.LogTo(Console.WriteLine)</code> on DbContextOptionsBuilder — logs generated SQL to the console."),
("DbUpdateException","EF Core wraps a database error (FK violation, unique constraint, etc.) in this exception."),
("SqlException","ADO.NET and Dapper throw this for SQL Server errors; check <code>Number</code> for the SQL Server error code."),
("Idempotent script","A migration SQL script that can be run multiple times safely (checks __EFMigrationsHistory).")],
["Compare Stopwatch timing honestly: single-query numbers vary ±30 %; run at least 100 iterations.",
"<code>LogTo</code> is for development only — it logs every query; remove it in production.",
"Catch <code>DbUpdateException</code> (EF), <code>SqlException</code> (ADO/Dapper) for FK and unique-key violations.",
"Always test 'down paths': not found, duplicate insert, deleted row update."],
f'''
<h3>1. Stopwatch timing harness</h3>
{C(r"""
using System.Diagnostics;
using StoreData.Core;

static async Task TimeAsync(string label, Func<Task> work, int iterations = 100)
{
    // warm up
    await work();

    var sw = Stopwatch.StartNew();
    for (int i = 0; i < iterations; i++) await work();
    sw.Stop();

    double avg = sw.Elapsed.TotalMilliseconds / iterations;
    Console.WriteLine($"  {label,-20} avg {avg,7:F2} ms over {iterations} iterations");
}

// Run the same GetAllAsync on each layer
ICatalogDal ado    = new AdoCatalogDal(ConnStr);
ICatalogDal dapper = new DapperCatalogDal(ConnStr);
ICatalogDal ef     = new EfCatalogDal(BuildDb(ConnStr));

Console.WriteLine("=== GetAllAsync (100 × 5 products) ===");
await TimeAsync("ADO.NET",  () => ado.GetAllAsync());
await TimeAsync("Dapper",   () => dapper.GetAllAsync());
await TimeAsync("EF Core",  () => ef.GetAllAsync());
""", "Benchmark.cs")}
{tip("With a local Docker SQL Server and 5 rows the numbers will all be < 5 ms and mostly indistinguishable. The gap only becomes meaningful at thousands of rows or under connection-pool pressure.")}

<h3>2. LogTo — see EF Core's SQL</h3>
{C(r"""
var opts = new DbContextOptionsBuilder<StoreDbContext>()
    .UseSqlServer(ConnStr)
    .LogTo(Console.WriteLine, Microsoft.Extensions.Logging.LogLevel.Information)
    .Options;

await using var db = new StoreDbContext(opts);
var products = await db.Products.Include(p => p.Category).Where(p => p.Price > 1000).ToListAsync();

// Console output (excerpt):
// info: 14/11/2026 12:34:56.789 RelationalEventId.CommandExecuted
//       Executed DbCommand (2ms) [Parameters=[@__p_0='1000'], CommandType=Text, CommandTimeout=30]
//       SELECT p.ProductId, p.Name, p.Price, p.CategoryId,
//              c.CategoryId, c.CategoryName
//       FROM Products AS p
//       INNER JOIN Categories AS c ON p.CategoryId = c.CategoryId
//       WHERE p.Price > @__p_0
""", "LogToDemo.cs")}

<h3>3. Try-to-break table</h3>
{table(["Scenario","Layer","Expected","How to verify"],[
["DB not running","ADO.NET","<code>SqlException</code>: connection refused","Stop Docker container, run GetAllAsync"],
["DB not running","Dapper","<code>SqlException</code>: same as above","Same"],
["DB not running","EF Core","<code>SqlException</code> wrapped in connection error","Same"],
["Duplicate CategoryName","ADO.NET","<code>SqlException</code> number 2601 (unique index)","INSERT duplicate category"],
["Duplicate CategoryName","Dapper","<code>SqlException</code> number 2601","INSERT duplicate category"],
["Duplicate CategoryName","EF Core","<code>DbUpdateException</code> → inner <code>SqlException</code> 2601","Add duplicate Category, SaveChanges"],
["Delete category with products","ADO.NET","<code>SqlException</code> 547 (FK violation)","DELETE from Categories WHERE FK exists"],
["Delete category with products","EF Core","<code>DbUpdateException</code> → 547 (DeleteBehavior.Restrict)","Remove() + SaveChanges"],
["GetById with unknown id","All three","Returns <code>null</code> / <code>null</code>","GetByIdAsync(99999)"],
["SQL injection attempt (ADO)","ADO.NET","Returns 0 rows; not executed as SQL","Pass <code>'; DROP TABLE Products; --</code> as name param"]])}

<h3>4. README template</h3>
{C(r"""
# StoreData — Week 15 micro-project

Three data-access layers (ADO.NET · Dapper · EF Core) behind one `ICatalogDal` interface.

## Prerequisites
- .NET 8 SDK
- Docker Desktop (for SQL Server 2022)
- `dotnet-ef` global tool

## Quick start
```bash
docker compose up -d
bash setup.sh           # creates StoreDb schema and seed data
dotnet run --project StoreData.App -- ado      # or dapper / ef
```

## Architecture
| Layer | File | NuGet |
|-------|------|-------|
| ADO.NET | Ado/AdoCatalogDal.cs | Microsoft.Data.SqlClient |
| Dapper  | Dapper/DapperCatalogDal.cs | Dapper |
| EF Core | Ef/EfCatalogDal.cs | Microsoft.EntityFrameworkCore.SqlServer |

## Running EF Core migrations
```bash
dotnet ef migrations add <Name> --project StoreData.Data --startup-project StoreData.App
dotnet ef database update
```
""", "README.md", lang="markdown")}

<h3>5. Git commands</h3>
{C(r"""
cd StoreData
git init
git add .
git commit -m "Week 15: StoreData — ADO.NET, Dapper and EF Core side by side"

# (optional) push to your GitHub
git remote add origin https://github.com/nayak22/dotnet-roadmap.git
git push -u origin main
""", "Terminal", lang="bash")}

<h3>6. Week 15 revision checklist</h3>
<h4>ADO.NET (Monday)</h4>
{ul(["SqlConnection / SqlCommand / SqlDataReader lifecycle","Parameters.Add vs AddWithValue","ExecuteScalar / ExecuteNonQuery / ExecuteReader","Connection pooling mechanism","SQL injection attack + parameterised fix","async pattern with CancellationToken"])}
<h4>Dapper (Tuesday)</h4>
{ul(["Query&lt;T&gt; and anonymous params","Multi-mapping and splitOn","QueryMultiple for two result sets","Stored procedure call with commandType","IN-list expansion","DynamicParameters for OUTPUT params"])}
<h4>EF Core — model/migrations (Wednesday)</h4>
{ul(["DbContext / DbSet","UseSqlServer and conventions","Data annotations vs Fluent API","Design-time factory purpose","add migration / update database / script","Reviewing generated migration files"])}
<h4>EF Core — relationships (Thursday)</h4>
{ul(["One-to-many FK and navigation properties","Many-to-many skip navigations","Explicit join entity with composite PK","Required vs optional / cascade behaviours","IEntityTypeConfiguration&lt;T&gt;","ApplyConfigurationsFromAssembly"])}
<h4>EF Core — CRUD and change tracking (Friday)</h4>
{ul(["EntityState lifecycle","How SaveChanges detects changes","AsNoTracking for read-only queries","context.Add vs context.Update difference","ExecuteDeleteAsync (EF 7+)","LogTo for SQL inspection"])}

<h3>7. Predict the output / does it compile? quiz</h3>
<details><summary>Q1. What does this print and why?</summary>
{C(r"""
await using var conn = new SqlConnection(ConnStr);
await conn.OpenAsync();
Console.WriteLine(conn.State);
await conn.CloseAsync();
Console.WriteLine(conn.State);
await conn.OpenAsync();
Console.WriteLine(conn.State);
""")}<b>Open, Closed, Open.</b> CloseAsync returns the connection to the pool (the TCP socket stays alive). The second OpenAsync checks it back out.</details>
<details><summary>Q2. Does this compile?</summary>
{C(r"""
IEnumerable<Product> products = await conn.QueryAsync<Product>("SELECT * FROM Products");
string first = products.First().Name;
string second = products.ElementAt(1).Name;
""")}<b>Yes, compiles and runs.</b> Dapper materialises the result before returning, so iterating twice is safe. <code>ElementAt</code> on an IEnumerable is O(n) for a list, but it won't re-query the DB.</details>
<details><summary>Q3. What happens?</summary>
{C(r"""
var cat = new Category { CategoryName = "Electronics" };   // already exists in DB
db.Categories.Add(cat);
await db.SaveChangesAsync();
""")}<b>DbUpdateException</b> wrapping a <code>SqlException</code> number 2601 (unique index violation on CategoryName).</details>
<details><summary>Q4. What does this UPDATE statement look like?</summary>
{C(r"""
var p = new Product { ProductId = 7, Price = 999m };
db.Products.Update(p);
await db.SaveChangesAsync();
""")}<b>UPDATE Products SET Name = '', Price = 999, CategoryId = 0 WHERE ProductId = 7</b> — context.Update marks ALL columns Modified. Name and CategoryId become their default values, overwriting real data. Always fetch first.</details>
<details><summary>Q5. How many SQL queries does this run?</summary>
{C(r"""
var products = await db.Products.AsNoTracking().ToListAsync();
var count    = await db.Products.CountAsync();
""")}<b>Two.</b> Each LINQ terminal (<code>ToListAsync</code>, <code>CountAsync</code>) is a separate database round trip. Use <code>QueryMultiple</code> (Dapper) or a single <code>SELECT … ; SELECT COUNT(*)</code> to combine them.</details>

<div class="note tip"><b>Next week:</b> Week 16 — EF Core in depth: eager vs lazy vs explicit loading, filtered Include, split queries, raw SQL with FromSql, interceptors, global query filters, owned entities, and performance diagnostics with MiniProfiler and execution plans.</div>
''',
iqs=[("Basic","Why benchmark all three layers against the same interface?","To measure fairly: same query, same data, same machine. The interface swap ensures we don't accidentally benchmark different SQL or different connection behaviour."),
("Intermediate","ADO.NET vs Dapper vs EF Core: how would you choose in a real project?","Use EF Core as the default for most entity CRUD and migrations. Drop to Dapper for complex reports, stored procedures and batch operations where SQL control matters. Use ADO.NET directly only for maximum performance paths or when neither ORM fits."),
("Intermediate","What is the SqlException.Number property?","The SQL Server error code. Common ones: 547 = FK violation, 2627 = PK violation, 2601 = unique index violation, 18456 = login failed. Catching SqlException and checking Number lets you give the user a meaningful error message."),
("Advanced","How would you implement a retry policy for transient SQL errors?","Wrap the DAL call in a Polly policy or use EF Core's built-in <code>EnableRetryOnFailure</code> in <code>UseSqlServer</code>. Transient SQL Server error codes include 1205 (deadlock), 40613, 40197. Retry with exponential back-off and a jitter.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","ADO.NET: SqlConnection, Command, DataReader","ADO.NET","Connection strings, parameters, injection attack/fix, pooling, async CRUD.","2 hrs"),
 (2,"TUE","Dapper: Query&lt;T&gt;, Execute, multi-mapping","Dapper","Micro-ORM on ADO.NET, anonymous params, IN-list, stored procs, QueryMultiple.","2 hrs"),
 (3,"WED","EF Core: DbContext, DbSet, migrations","EF Core setup","UseSqlServer, conventions, dotnet ef add/update/script, design-time factory.","2 hrs"),
 (4,"THU","Relationships: Fluent API and IEntityTypeConfiguration","EF Relationships","One-to-many, many-to-many, skip navigations, cascade, Fluent API.","2 hrs"),
 (5,"FRI","CRUD with EF Core and change tracking","EF CRUD","Add/Read/Update/Delete, EntityState, AsNoTracking, SaveChanges internals.","2 hrs"),
 (6,"SAT","StoreData.sln — ADO.NET · Dapper · EF Core side by side","Project: StoreData","ICatalogDal with three implementations, Docker + sqlcmd setup, console menu.","4 hrs"),
 (7,"SUN","Compare, try to break, README and git","Week wrap-up","Stopwatch harness, LogTo, edge-case table, checklist, quiz, next week preview.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week15.html", 15,
      "Week 15 — ADO.NET, Dapper and EF Core Basics", "Phase 2", "~18 hrs",
      ["Phase 2 · Week 15 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "CRUD ×3"],
      "Data access is the backbone of every business application. This week you descend from raw ADO.NET through Dapper to EF Core, understanding exactly what each layer adds — and costs. You'll handle SQL injection, map relationships, run migrations, and wire all three approaches behind a single interface in the StoreData micro-project.",
      cards, days)
print("built")
