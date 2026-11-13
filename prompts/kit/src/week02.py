import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Classes, objects, constructors, properties and fields",
"Model a real business entity as a class with validated properties, sensible constructors and a useful ToString().",
[("Class","A blueprint that defines the data (state) and behaviour (methods) of a type. A reference type."),
("Object / instance","A concrete value created from a class with <code>new</code>; each object has its own copy of instance data."),
("Field","A variable declared directly in a class that stores the object's data. Private by convention, named <code>_camelCase</code>."),
("Property","A member that looks like a field to callers but runs <code>get</code>/<code>set</code> accessors, so you can validate or compute."),
("Backing field","The private field a full property reads and writes."),
("Auto-property","<code>{ get; set; }</code> — the compiler generates a hidden backing field."),
("Init-only setter","<code>{ get; init; }</code> — the property can be set only in a constructor or object initializer (C# 9)."),
("required member","C# 11 modifier forcing callers to set a property in the object initializer."),
("Computed property","A property with no storage that calculates its value: <code>public decimal Annual =&gt; Monthly * 12;</code>"),
("Constructor","A special method with the class's name and no return type that initialises a new object."),
("Constructor chaining","Calling another constructor of the same class with <code>: this(...)</code> to avoid duplicate code."),
("Primary constructor","C# 12 syntax that declares constructor parameters on the class line: <code>class Invoice(string number)</code>."),
("Object initializer","<code>new Employee { Name = \"Asha\" }</code> — sets accessible properties right after construction."),
("this","A reference to the current object inside its own members."),
("Member","Anything declared inside a class: fields, properties, methods, constructors, events, nested types.")],
["A class is the design; an object is one thing built from it. You can create many objects from one class.",
"Keep fields private; expose data through properties.",
"Validate in the constructor and in property setters so an object can never be in an invalid state.",
"Use <code>init</code> / <code>private set</code> for values that shouldn't change after creation.",
"Chain constructors with <code>: this(...)</code> instead of copying code.",
"Override <code>ToString()</code> so objects print something useful in logs and the debugger."],
f'''
<h3>1. Classes and objects</h3>
<p>A <b>class</b> describes what a thing <i>has</i> (data) and what it <i>does</i> (behaviour). An <b>object</b> is one instance of that class living on the heap. The variable holds a reference to it, which is why classes behave as reference types (Week 1, Day 2).</p>
{C(r"""
public class Product
{
    // Fields: the object's data (private by convention)
    private string _name;
    private decimal _price;

    // Constructor: runs when you call `new`
    public Product(string name, decimal price)
    {
        _name = name;
        _price = price;
    }

    // Method: behaviour that uses the object's data
    public string Describe() => $"{_name} costs {_price:C}";
}
""", "Product.cs")}
{C(r"""
var laptop = new Product("Laptop", 65000m);   // object #1
var mouse  = new Product("Mouse", 799m);      // object #2 — its own separate data

Console.WriteLine(laptop.Describe());   // Laptop costs ₹65,000.00   (en-IN culture)
Console.WriteLine(mouse.Describe());    // Mouse costs ₹799.00

var sameLaptop = laptop;                // copies the REFERENCE, not the object
Console.WriteLine(ReferenceEquals(laptop, sameLaptop)); // True
""", "Program.cs")}
{tip("<code>:C</code> and <code>:N</code> format using the current culture: the ₹ output above assumes en-IN, while other <code>:N</code> outputs in these notes show en-US-style grouping (150,000); under en-IN you'd see lakh grouping (1,50,000). Also, when a sample shows a class and the code that uses it together, put the usage in <code>Program.cs</code> or above the class: top-level statements must come before type declarations in a file (error CS8803).")}

<h3>2. Fields</h3>
<p>Fields hold state. Unassigned fields get default values (0, false, null). Mark a field <code>readonly</code> when it is assigned once in the constructor and never again.</p>
{C(r"""
public class Counter
{
    private int _count;                          // defaults to 0
    private readonly DateTime _createdAt = DateTime.UtcNow;   // field initializer
    private readonly List<string> _log = new();  // the reference is readonly, the list contents are not

    public void Increment()
    {
        _count++;
        _log.Add($"Incremented to {_count}");
    }
}
""")}
{warn("Public fields like <code>public decimal Price;</code>. Anyone can set a negative price and you can never add validation later without breaking callers. Use a property.", "Avoid")}

<h3>3. Properties</h3>
<p>Properties are the public face of an object's data. They look like fields to the caller, but they are really methods, so you can validate, compute or restrict access.</p>
{C(r"""
public class Employee
{
    private decimal _monthlySalary;                 // backing field

    // 1. Full property with validation
    public decimal MonthlySalary
    {
        get => _monthlySalary;
        set
        {
            if (value < 0)
                throw new ArgumentOutOfRangeException(nameof(value), "Salary can't be negative");
            _monthlySalary = value;
        }
    }

    // 2. Auto-property with a default value
    public string Name { get; set; } = "";

    // 3. Read-only from outside the class
    public int Id { get; private set; }

    // 4. Init-only: settable only while the object is being created
    public string Department { get; init; } = "General";

    // 5. Required (C# 11): the caller MUST set it in the initializer
    public required string Email { get; init; }

    // 6. Computed: no storage, calculated on every read
    public decimal AnnualSalary => MonthlySalary * 12;
}
""", "Employee.cs")}
{C(r"""
var e = new Employee
{
    Name = "Asha",
    Email = "asha@example.com",      // leave this out → compile error CS9035
    MonthlySalary = 85_000m,
    Department = "IT"
};

Console.WriteLine(e.AnnualSalary);   // 1020000
// e.Department = "HR";              // ❌ init-only after creation
// e.Id = 5;                         // ❌ setter is private
// e.MonthlySalary = -1;             // throws ArgumentOutOfRangeException
""")}
{table(["Syntax","Who can set it","When"],[
["<code>{ get; set; }</code>","Anyone","Any time"],
["<code>{ get; private set; }</code>","Only the class","Any time"],
["<code>{ get; init; }</code>","Anyone","Only during construction / initializer"],
["<code>{ get; }</code>","Only the constructor","Once"],
["<code>=&gt; expression</code>","Nobody (computed)","—"]])}

<h3>4. Constructors</h3>
<p>A constructor guarantees an object starts life valid. If you declare no constructor, C# gives you a public parameterless one. As soon as you write any constructor, that free one disappears.</p>
{C(r"""
public class Order
{
    public int Id { get; }
    public string Customer { get; }
    public DateTime CreatedAt { get; }
    public decimal Total { get; private set; }

    // Chains to the main constructor — no duplicated logic
    public Order() : this(0, "Walk-in") { }

    // Main constructor: validate everything here
    public Order(int id, string customer)
    {
        if (string.IsNullOrWhiteSpace(customer))
            throw new ArgumentException("Customer is required", nameof(customer));

        Id = id;
        Customer = customer.Trim();
        CreatedAt = DateTime.UtcNow;
    }

    public void AddLine(decimal unitPrice, int quantity)
    {
        if (quantity <= 0) throw new ArgumentOutOfRangeException(nameof(quantity));
        Total += unitPrice * quantity;
    }

    public override string ToString() => $"Order #{Id} for {Customer}: {Total:N2}";
}
""", "Order.cs")}
{C(r"""
var order = new Order(101, "Ravi Traders");
order.AddLine(250m, 4);
order.AddLine(99.5m, 2);
Console.WriteLine(order);          // Order #101 for Ravi Traders: 1,199.00

var walkIn = new Order();
Console.WriteLine(walkIn.Customer); // Walk-in
""")}

<h4>Primary constructors (C# 12)</h4>
<p>For simple classes, declare parameters on the class itself. The parameters are in scope across the whole class body.</p>
{C(r"""
public class Invoice(string number, decimal amount)
{
    public string Number { get; } = number;
    public decimal Amount { get; } = amount;
    public decimal Gst => Amount * 0.18m;        // use the property, not the parameter

    public override string ToString() => $"{Number}: {Amount:N2} + GST {Gst:N2}";
}

var inv = new Invoice("INV-2026-001", 10_000m);
Console.WriteLine(inv);   // INV-2026-001: 10,000.00 + GST 1,800.00
""", "Invoice.cs")}
{tip("Primary-constructor parameters are not properties and are mutable. If callers need the value, copy it into a property like <code>Number</code> above. Using the parameter in both a property initializer and a method triggers warning CS9124.")}

<h3>5. this, methods and ToString()</h3>
{C(r"""
public class Rectangle
{
    public double Width { get; }
    public double Height { get; }

    public Rectangle(double width, double height)
    {
        this.Width = width;        // `this.` is optional here, required only when names clash
        this.Height = height;
    }

    public double Area() => Width * Height;

    // Returns a NEW object instead of changing this one
    public Rectangle Scale(double factor) => new(Width * factor, Height * factor);

    public bool IsLargerThan(Rectangle other) => this.Area() > other.Area();

    public override string ToString() => $"{Width} × {Height}";
}
""")}

<h3>6. Object lifetime</h3>
<ul>
<li><code>new</code> allocates the object on the managed heap and runs the constructor.</li>
<li>Variables hold references. When no reference reaches an object, the garbage collector can reclaim it. You never free memory yourself.</li>
<li>A reference that points to nothing is <code>null</code>; using it throws <code>NullReferenceException</code>.</li>
</ul>
{C(r"""
Order? current = new Order(1, "Meena");
current = null;               // the Order object is now unreachable → eligible for GC
// current.AddLine(10, 1);    // NullReferenceException at runtime (and a compiler warning)
""")}
''',
["Exposing public fields instead of properties.",
"Forgetting that adding any constructor removes the default parameterless one.",
"Doing validation in the UI instead of in the class, so invalid objects can still be created elsewhere.",
"Setters on values that should never change after creation (IDs, created dates).",
"Huge constructors with 8+ parameters. Group related values into their own class."],
("40 min", ["Create a <code>Student</code> class: Id (read-only), Name (required, non-empty), Email (init-only, must contain @), Marks (0–100 validated), and a computed <code>Grade</code>.",
"Add two constructors and chain one to the other.",
"Override <code>ToString()</code> and create three students in <code>Program.cs</code>, then print them."]),
[("What happens to the default constructor when you add your own?","It's no longer generated. If callers still need <code>new T()</code>, declare a parameterless constructor explicitly."),
("Why use a property instead of a public field?","Properties let you add validation, make setters private or init-only, compute values and change the implementation later without breaking callers. Data binding and serializers also work with properties."),
("init vs private set?","<code>init</code> can be set by anyone, but only during object creation. <code>private set</code> can be changed at any time, but only by code inside the class.")],
[("Basic","What is the difference between a class and an object?","A class is a type definition: a blueprint describing data and behaviour. An object is a runtime instance of that class with its own state, allocated on the heap. One class can produce many objects."),
("Basic","What is the difference between a field and a property?","A field is a variable that stores data directly. A property is a pair of accessor methods (get/set/init) that controls access to data, usually wrapping a private backing field. Properties support validation, computed values, access restrictions and are what frameworks like EF Core and JSON serializers bind to."),
("Basic","What is constructor chaining?","Calling one constructor from another of the same class using <code>: this(args)</code>, or the base class using <code>: base(args)</code>. It keeps initialisation logic in one place."),
("Intermediate","What are init-only setters and required members?","<code>init</code> (C# 9) allows a property to be set during construction or in an object initializer, then makes it immutable. <code>required</code> (C# 11) makes the compiler enforce that callers set the member in the initializer, unless a constructor marked <code>[SetsRequiredMembers]</code> does it."),
("Intermediate","What are primary constructors in C# 12 and what is a pitfall?","They declare constructor parameters on the type declaration, available throughout the class body. The pitfall: the parameters are captured as hidden mutable fields, not properties. Using a parameter both to initialise a property and elsewhere creates two copies of the state, which is why the compiler warns (CS9124)."),
("Intermediate","Can a constructor be private? Why would you do that?","Yes. Private constructors prevent outside instantiation. They're used for static-only classes, the Singleton pattern, and factory methods like <code>Order.Create(...)</code> that validate or choose a subtype before constructing.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Encapsulation, access modifiers and static members",
"Hide an object's internals behind a small, safe public surface, choose the right access modifier, and know when something belongs to the type instead of an instance.",
[("Encapsulation","Bundling data with the methods that operate on it and hiding internal state so it can only change through valid operations."),
("Invariant","A rule that must always hold for an object, e.g. a bank balance is never negative."),
("Access modifier","A keyword that controls where a type or member can be used: public, private, protected, internal, protected internal, private protected, file."),
("public","Accessible from any code."),
("private","Accessible only inside the same class (the default for members)."),
("protected","Accessible inside the class and classes that derive from it."),
("internal","Accessible anywhere in the same assembly (project). The default for top-level types."),
("protected internal","Same assembly OR derived classes in any assembly."),
("private protected","Derived classes in the same assembly only (C# 7.2)."),
("file","Type visible only within its source file (C# 11), used mostly by source generators."),
("Static member","Belongs to the type itself, shared by all instances; accessed as <code>TypeName.Member</code>."),
("Static constructor","Parameterless constructor that runs once, automatically, before the type is first used."),
("Static class","A class that can't be instantiated or inherited and contains only static members."),
("static readonly","A field set once at runtime and shared by all instances; unlike const it can hold any type."),
("Namespace","A logical grouping of types that prevents name clashes, e.g. <code>Library.Core.Models</code>.")],
["Make everything private first, then open up only what callers truly need.",
"Expose behaviour (<code>Deposit</code>, <code>Withdraw</code>) instead of raw setters (<code>Balance = ...</code>).",
"Return <code>IReadOnlyList&lt;T&gt;</code>, never your internal <code>List&lt;T&gt;</code>.",
"Static = one copy per type; instance = one copy per object.",
"Use static classes for stateless helpers; avoid static mutable state (hard to test, not thread-safe).",
"const for compile-time literals, static readonly for values computed at startup."],
f'''
<h3>1. Encapsulation by example</h3>
<p>Start with what goes wrong without it. With public fields, any caller can break the account's rules:</p>
{C(r"""
public class BadAccount
{
    public decimal Balance;            // anyone can write anything
}

var acc = new BadAccount();
acc.Balance = -50_000;                 // invariant broken, nobody stopped it
""")}
<p>An encapsulated version exposes <i>operations</i> and keeps state private. Every change goes through code that enforces the rules.</p>
{C(r"""
public class BankAccount
{
    private readonly List<string> _transactions = new();

    public string AccountNumber { get; }
    public string Owner { get; }
    public decimal Balance { get; private set; }               // read publicly, write privately
    public IReadOnlyList<string> Transactions => _transactions; // read-only view

    public BankAccount(string accountNumber, string owner, decimal openingBalance = 0)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(accountNumber);
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        if (openingBalance < 0)
            throw new ArgumentOutOfRangeException(nameof(openingBalance));

        AccountNumber = accountNumber;
        Owner = owner;
        Balance = openingBalance;
        Log($"Opened with {openingBalance:N2}");
    }

    public void Deposit(decimal amount)
    {
        if (amount <= 0)
            throw new ArgumentOutOfRangeException(nameof(amount), "Deposit must be positive");
        Balance += amount;
        Log($"Deposit {amount:N2}");
    }

    public bool TryWithdraw(decimal amount)
    {
        if (amount <= 0 || amount > Balance) return false;   // invariant: never negative
        Balance -= amount;
        Log($"Withdraw {amount:N2}");
        return true;
    }

    private void Log(string message) => _transactions.Add($"{DateTime.Now:g}  {message}");
}
""", "BankAccount.cs")}
{C(r"""
var account = new BankAccount("SB-00123", "Samrath", 5_000m);
account.Deposit(2_500m);
bool ok = account.TryWithdraw(10_000m);    // false — insufficient funds

Console.WriteLine($"{account.Balance:N2}"); // 7,500.00
foreach (var t in account.Transactions) Console.WriteLine(t);

// account.Balance = 1_000_000;            // ❌ setter is private
// account.Transactions.Add("hack");       // ❌ IReadOnlyList has no Add
""")}
{tip("Returning <code>IReadOnlyList&lt;T&gt;</code> stops casual mutation, but a determined caller could cast it back to <code>List&lt;T&gt;</code>. For a hard guarantee return <code>_transactions.AsReadOnly()</code> or a copy.")}

<h3>2. Access modifiers</h3>
{table(["Modifier","Same class","Derived (same project)","Same project","Derived (other project)","Anywhere"],[
["<code>private</code>","✓","","","",""],
["<code>private protected</code>","✓","✓","","",""],
["<code>protected</code>","✓","✓","","✓",""],
["<code>internal</code>","✓","✓","✓","",""],
["<code>protected internal</code>","✓","✓","✓","✓",""],
["<code>public</code>","✓","✓","✓","✓","✓"]])}
<ul>
<li>Members of a class default to <code>private</code>; top-level classes default to <code>internal</code>.</li>
<li><code>internal</code> is perfect for helpers inside a class library that the app project shouldn't touch. You'll use it in Saturday's project for <code>IsAvailable</code>'s setter.</li>
<li>Use <code>[assembly: InternalsVisibleTo("MyApp.Tests")]</code> to let a test project see internals.</li>
</ul>

<h3>3. Static members</h3>
<p>Instance members belong to each object. Static members belong to the type and exist once, no matter how many objects you create.</p>
{C(r"""
public class Customer
{
    private static int _nextId = 1;           // shared counter
    public static int Count { get; private set; }

    public int Id { get; }                    // per-object
    public string Name { get; }

    public Customer(string name)
    {
        Id = _nextId++;
        Name = name;
        Count++;
    }

    // Static factory method: a named way to create objects
    public static Customer CreateGuest() => new("Guest");
}

var a = new Customer("Priya");
var b = new Customer("Karan");
var g = Customer.CreateGuest();

Console.WriteLine($"{a.Id} {b.Id} {g.Id}");   // 1 2 3
Console.WriteLine(Customer.Count);            // 3 — accessed through the TYPE
// a.Count                                    // ❌ can't access static via instance
""", "Customer.cs")}
{warn("The <code>_nextId++</code> counter above isn't thread-safe. Two threads could get the same id. You'll fix this with <code>Interlocked.Increment</code> in Week 7; in real apps the database generates ids.", "Watch out")}

<h4>Static constructors and static classes</h4>
{C(r"""
public class AppInfo
{
    public static readonly string Environment;
    public static readonly DateTime StartedAt;

    // Runs exactly once, before the first access to AppInfo
    static AppInfo()
    {
        Environment = System.Environment.GetEnvironmentVariable("APP_ENV") ?? "Development";
        StartedAt = DateTime.UtcNow;
    }
}

public static class Gst                      // cannot be instantiated or inherited
{
    public const decimal StandardRate = 0.18m;
    public static decimal Add(decimal amount, decimal rate = StandardRate) => amount + amount * rate;
    public static decimal Extract(decimal grossAmount, decimal rate = StandardRate) => grossAmount - grossAmount / (1 + rate);
}

Console.WriteLine(Gst.Add(1000m));           // 1180.00
Console.WriteLine(AppInfo.Environment);      // Development
""")}

<h3>4. const vs readonly vs static readonly</h3>
{table(["","const","readonly","static readonly"],[
["Set when","Compile time","Declaration or constructor","Declaration or static constructor"],
["Per","Type (implicitly static)","Instance","Type"],
["Allowed types","Built-in numeric types (incl. decimal), bool, char, string, enum; other reference types only as null","Any","Any"],
["Example","<code>const int MaxLoans = 3;</code>","<code>readonly Guid _id;</code>","<code>static readonly HttpClient Client = new();</code>"]])}
{warn("A <code>public const</code> in a library is copied into every caller's compiled code. If you change it, callers keep the old value until they recompile. Use <code>public static readonly</code> for values that might change.", "Gotcha")}

<h3>5. Namespaces</h3>
{C(r"""
// File-scoped namespace (C# 10): applies to the whole file, saves one indent level
namespace Library.Core.Models;

public class Book { /* ... */ }
""", "Book.cs")}
{C(r"""
using Library.Core.Models;                 // import a namespace
using Models = Library.Core.Models;        // alias, useful when two namespaces clash

var b = new Book();
var b2 = new Models.Book();
""")}
<p>Convention: the namespace mirrors the folder path (<code>Library.Core/Models/Book.cs</code> → <code>Library.Core.Models</code>).</p>
''',
["Making everything public because it's easier right now.",
"Returning a mutable internal collection from a getter.",
"Storing per-user or per-request data in static fields — every user shares it.",
"Using <code>public const</code> in a shared library for values that may change.",
"Static classes that hold state; they can't be mocked in tests."],
("40 min", ["Build <code>BankAccount</code> as above, then add <code>Transfer(BankAccount to, decimal amount)</code> that only succeeds if the withdrawal succeeds.",
"Add a static <code>TotalAccountsOpened</code> counter and a static <code>InterestRate</code> property, with an instance method <code>ApplyMonthlyInterest()</code>.",
"Try to break the account from <code>Program.cs</code> (negative deposit, editing Transactions). Note every compiler or runtime error you get."]),
[("What's the default access modifier for a class member? For a top-level class?","Members default to <code>private</code>. Top-level classes default to <code>internal</code>."),
("Can a static method use instance fields?","Not directly — there is no <code>this</code>. It needs an instance passed in, e.g. <code>static void Print(Customer c)</code>."),
("When does a static constructor run?","Once per type per app domain, automatically, just before the first instance is created or any static member is accessed. You can't call it or pass parameters to it.")],
[("Basic","What is encapsulation and why does it matter?","Encapsulation hides an object's internal state and exposes only controlled operations, so invariants can't be broken from outside. It reduces coupling: you can change the internals without changing callers, and bugs are localised to the class that owns the data."),
("Basic","Explain all the access modifiers in C#.","public (everywhere), private (same class), protected (class + derived), internal (same assembly), protected internal (same assembly OR derived anywhere), private protected (derived classes in the same assembly), and file (C# 11, same source file, types only)."),
("Basic","What is the difference between static and instance members?","Instance members belong to each object and need an instance to be used. Static members belong to the type, exist once, are accessed via the type name, and can't access instance members without a reference."),
("Intermediate","What is a static class and when would you use one?","A sealed, abstract-at-IL-level class with only static members and no instances. Use it for stateless utilities and extension methods (e.g. Math, Path). Avoid it for anything that needs state, polymorphism, or mocking in tests; use a regular class registered in DI instead."),
("Intermediate","const vs static readonly — which would you use for a URL in a shared library?","static readonly. const values are baked into consuming assemblies at compile time, so changing them requires recompiling every consumer. static readonly is read at runtime and can be any type."),
("Intermediate","Why are mutable static fields dangerous in web apps?","They're shared by every request and thread in the process. Concurrent writes cause race conditions, data can leak between users, and tests interfere with each other. Use scoped services or a proper store instead.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Inheritance, base, virtual/override and sealed",
"Build a small class hierarchy, reuse and extend base behaviour correctly, and know when inheritance is the wrong tool.",
[("Inheritance","A mechanism where a derived class acquires the members of a base class, modelling an \"is-a\" relationship."),
("Base class (parent)","The class being inherited from, e.g. <code>Employee</code>."),
("Derived class (child)","The class that inherits, e.g. <code>Manager : Employee</code>."),
("Single inheritance","C# classes can inherit from only one base class (but implement many interfaces)."),
("base","Keyword to call the base class's constructor (<code>: base(...)</code>) or members (<code>base.CalculatePay()</code>)."),
("virtual","Marks a base member that derived classes are allowed to override."),
("override","Replaces a virtual/abstract member's implementation in a derived class; resolved at runtime."),
("new (modifier)","Hides a base member with a new one; the call is resolved by the variable's compile-time type."),
("sealed class","A class that can't be inherited."),
("sealed override","An override that further-derived classes can't override again."),
("System.Object","The ultimate base of every type; provides ToString, Equals, GetHashCode, GetType."),
("Composition","Building a class from other objects it holds (\"has-a\") instead of inheriting from them."),
("Method resolution","Choosing which implementation runs: virtual calls use the object's runtime type.")],
["Inherit only for genuine \"is-a\" relationships: a Manager <i>is an</i> Employee.",
"Base constructor runs before the derived constructor's body; pass arguments with <code>: base(...)</code>.",
"A method must be <code>virtual</code> (or abstract) in the base before it can be overridden.",
"<code>override</code> = polymorphic; <code>new</code> = hiding, usually a smell.",
"Seal classes you didn't design for inheritance.",
"Prefer composition when you just want to reuse code."],
f'''
<h3>1. A simple hierarchy</h3>
{C(r"""
public class Employee
{
    public string Name { get; }
    public decimal BaseSalary { get; }

    public Employee(string name, decimal baseSalary)
    {
        Name = name;
        BaseSalary = baseSalary;
        Console.WriteLine("  Employee constructor");
    }

    // virtual: derived classes MAY replace this
    public virtual decimal CalculatePay() => BaseSalary;

    public override string ToString() => $"{GetType().Name,-8} {Name,-8} pays {CalculatePay(),10:N0}";
}

public class Manager : Employee
{
    public decimal Bonus { get; }

    public Manager(string name, decimal baseSalary, decimal bonus)
        : base(name, baseSalary)                    // base constructor first
    {
        Bonus = bonus;
        Console.WriteLine("  Manager constructor");
    }

    // Extend the base behaviour instead of rewriting it
    public override decimal CalculatePay() => base.CalculatePay() + Bonus;
}

public sealed class Intern : Employee               // nobody can derive from Intern
{
    public Intern(string name) : base(name, 20_000m) { }
}
""", "Employees.cs")}
{C(r"""
Console.WriteLine("Creating manager:");
var m = new Manager("Divya", 120_000m, 30_000m);
// Creating manager:
//   Employee constructor     ← base runs first
//   Manager constructor

Employee[] staff = [ new Employee("Arjun", 60_000m), m, new Intern("Zoya") ];
foreach (var e in staff) Console.WriteLine(e);
// Employee Arjun    pays     60,000
// Manager  Divya    pays    150,000   ← Manager's override ran via an Employee reference
// Intern   Zoya     pays     20,000
""")}

<h3>2. What a derived class gets</h3>
<ul>
<li>All public, protected and internal members of the base (private members exist in the object but aren't accessible).</li>
<li>Constructors are <b>not</b> inherited; each class declares its own and chains with <code>: base(...)</code>.</li>
<li>If the base has no parameterless constructor, every derived constructor must call <code>base(...)</code> explicitly.</li>
</ul>
{C(r"""
public class Vehicle
{
    protected int Wheels { get; }                 // visible to derived classes only
    private string _secret = "VIN-123";           // not accessible in Car

    protected Vehicle(int wheels) => Wheels = wheels;
}

public class Car : Vehicle
{
    public Car() : base(4) { }
    public string Describe() => $"Car with {Wheels} wheels";   // ✓ protected
    // public string Vin => _secret;                             // ❌ private in Vehicle
}
""")}

<h3>3. override vs new (hiding)</h3>
<p>This difference is a classic interview question. Run it and look at the output carefully.</p>
{C(r"""
class Notification
{
    public virtual string Channel() => "generic";
    public string Priority() => "normal";
}

class SmsNotification : Notification
{
    public override string Channel() => "sms";       // overrides
    public new string Priority() => "high";          // hides
}

Notification n = new SmsNotification();               // base-type variable, derived object

Console.WriteLine(n.Channel());    // sms     ← override: the RUNTIME type decides
Console.WriteLine(n.Priority());   // normal  ← new: the COMPILE-TIME type decides

var s = (SmsNotification)n;
Console.WriteLine(s.Priority());   // high
""")}
{table(["","override","new"],[
["Base member must be","virtual / abstract / override","anything"],
["Which runs via a base reference","Derived version","Base version"],
["Polymorphic?","Yes","No"],
["Typical use","Normal extension","Rare: a base you don't control added a clashing member"]])}
{warn("Without either keyword, a same-named member hides the base and you get warning CS0108. Decide deliberately.", "Rule")}

<h3>4. sealed and System.Object</h3>
{C(r"""
public class Report
{
    public virtual string Render() => "base report";
}

public class SalesReport : Report
{
    public sealed override string Render() => "sales report";   // stops further overriding
}

public class RegionalSalesReport : SalesReport
{
    // public override string Render() => "...";   // ❌ CS0239: Render is sealed
}
""")}
<p>Every class inherits from <code>object</code>. The members you'll override most:</p>
{table(["Member","Default behaviour","Override when"],[
["<code>ToString()</code>","Fully qualified type name","Always useful for logging and debugging"],
["<code>Equals(object)</code>","Reference equality for classes","Two objects with the same data should be equal"],
["<code>GetHashCode()</code>","Based on reference","Always together with Equals"],
["<code>GetType()</code>","Runtime type (not overridable)","—"]])}
{C(r"""
public class Isbn
{
    public string Value { get; }
    public Isbn(string value) => Value = value.Replace("-", "");

    public override bool Equals(object? obj) => obj is Isbn other && other.Value == Value;
    public override int GetHashCode() => Value.GetHashCode();
    public override string ToString() => Value;
}

Console.WriteLine(new Isbn("978-0132350884").Equals(new Isbn("9780132350884")));  // True
""")}
{tip("Records (Week 3) generate value-based Equals, GetHashCode and ToString for you.")}

<h3>5. Composition over inheritance</h3>
<p>Inheritance couples the child tightly to the parent. If you only want to <i>reuse</i> code, hold an object instead.</p>
{C(r"""
// ❌ Inheritance for reuse: an OrderService is NOT a Logger
public class OrderService : FileLogger { }

// ✓ Composition: an OrderService HAS a logger
public class OrderService
{
    private readonly FileLogger _logger;
    public OrderService(FileLogger logger) => _logger = logger;

    public void Place(int orderId) => _logger.Write($"Order {orderId} placed");
}

public class FileLogger
{
    public void Write(string message) => File.AppendAllText("app.log", message + Environment.NewLine);
}
""")}
<p>Ask "is-a or has-a?" before writing the colon. Deep hierarchies (more than 2–3 levels) are hard to change; on Friday you'll see how interfaces make composition even more flexible.</p>
''',
["Inheriting just to reuse a method (use composition).",
"Forgetting <code>virtual</code> in the base and then wondering why the override won't compile.",
"Using <code>new</code> to \"fix\" warning CS0108 without understanding the behaviour.",
"Calling virtual methods from a base constructor — the derived override runs before the derived constructor has initialised its fields.",
"Overriding Equals without GetHashCode, which breaks dictionaries and HashSets."],
("40 min", ["Create <code>Vehicle</code> (Brand, Year, virtual <code>RentalPerDay()</code>) and derive <code>Car</code>, <code>Bike</code> and <code>Truck</code> with different pricing. Truck adds a per-ton surcharge via <code>base.RentalPerDay()</code>.",
"Put them in a <code>Vehicle[]</code> and print each one's rental for 3 days.",
"Write the override-vs-new demo yourself and explain each output line in a comment."]),
[("Does C# support multiple inheritance?","Not for classes; a class has exactly one base class. A class can implement any number of interfaces."),
("Are constructors inherited?","No. A derived class must declare its own constructors and chain to a base constructor."),
("What does sealed do on a method?","Applied to an override, it prevents classes further down the hierarchy from overriding it again.")],
[("Basic","What is inheritance and what are its benefits and drawbacks?","Inheritance lets a derived class reuse and specialise a base class (an is-a relationship). Benefits: code reuse and polymorphism. Drawbacks: tight coupling, fragile base class problem (base changes break children), and rigid hierarchies that are hard to refactor."),
("Basic","What is the difference between virtual and abstract?","A virtual member has an implementation that derived classes may override. An abstract member has no implementation, can only exist in an abstract class, and derived non-abstract classes must override it."),
("Basic","What is the order of constructor execution in an inheritance chain?","Field initialisers run from derived to base, then constructor bodies run from base to derived. So the base constructor body always completes before the derived constructor body runs."),
("Intermediate","Explain method hiding (new) vs overriding (override).","Override replaces a virtual method; calls through any reference use the runtime type's implementation (dynamic dispatch). new hides the base member; which version runs depends on the compile-time type of the variable. Hiding breaks polymorphism and is rarely what you want."),
("Intermediate","Why is calling a virtual method in a constructor dangerous?","The base constructor runs first, but a virtual call dispatches to the most-derived override, which may use fields the derived constructor hasn't set yet, causing nulls or wrong values."),
("Intermediate","When would you prefer composition over inheritance?","When the relationship is has-a or uses-a, when you need to swap behaviour at runtime, when you'd otherwise need multiple inheritance, or when the base class isn't designed for extension. Composition with interfaces gives looser coupling and easier testing.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Polymorphism and abstract classes",
"Write code that works with a base type and lets each subtype supply its own behaviour, using abstract classes to enforce what every subtype must implement.",
[("Polymorphism","\"Many forms\": the same call behaves differently depending on the object's actual type."),
("Compile-time polymorphism","Static binding decided by the compiler: method and operator overloading."),
("Runtime polymorphism","Dynamic binding decided at runtime through virtual/abstract members and overriding."),
("Dynamic dispatch","The runtime looking up the most-derived override via the object's method table (vtable)."),
("Abstract class","A class marked <code>abstract</code> that can't be instantiated and may contain abstract members."),
("Abstract member","A method or property with no body that every non-abstract derived class must override."),
("Concrete class","A non-abstract class you can instantiate."),
("Template Method pattern","A base class defines the fixed steps of an algorithm; subclasses fill in specific steps."),
("Upcasting","Treating a derived object as its base type; implicit and always safe."),
("Downcasting","Converting a base reference to a derived type; explicit and may fail."),
("is / as","<code>is</code> tests a type (and can declare a variable); <code>as</code> casts or returns null."),
("Operator overloading","Defining what operators like + or == mean for your own type.")],
["Write code against the base type; let each subtype supply the details.",
"An abstract class is a partial template: shared code plus required gaps.",
"Use <code>abstract</code> when every subtype must provide it, <code>virtual</code> when a default makes sense.",
"Adding a new subtype shouldn't require editing the code that loops over the base type (Open/Closed).",
"Prefer polymorphism over <code>if (x is A) … else if (x is B) …</code> chains.",
"Downcast with pattern matching: <code>if (shape is Circle c)</code>."],
f'''
<h3>1. Two kinds of polymorphism</h3>
{table(["","Compile-time (static)","Runtime (dynamic)"],[
["Mechanism","Overloading methods/operators","Overriding virtual/abstract members"],
["Decided by","Compiler, from argument types","CLR, from the object's runtime type"],
["Example","<code>Area(r)</code> vs <code>Area(w, h)</code>","<code>shape.Area()</code> on a Circle or a Rectangle"]])}

<h3>2. Abstract classes</h3>
<p>Every shape has an area, but there's no sensible area for a generic "shape". Make the base abstract and force each concrete shape to provide it.</p>
{C(r"""
public abstract class Shape
{
    public string Name { get; }

    protected Shape(string name) => Name = name;    // protected: only subclasses call it

    public abstract double Area();                  // no body — must be overridden
    public abstract double Perimeter();

    public virtual string Describe() => $"{Name,-9} area {Area(),8:F2}  perimeter {Perimeter(),7:F2}";
}

public class Circle(double radius) : Shape("Circle")
{
    public double Radius => radius;
    public override double Area() => Math.PI * radius * radius;
    public override double Perimeter() => 2 * Math.PI * radius;
}

public class Rectangle(double width, double height) : Shape("Rectangle")
{
    public double Width => width;
    public double Height => height;
    public override double Area() => width * height;
    public override double Perimeter() => 2 * (width + height);
}

public class Triangle(double a, double b, double c) : Shape("Triangle")
{
    public override double Perimeter() => a + b + c;
    public override double Area()
    {
        double s = Perimeter() / 2;                               // Heron's formula
        return Math.Sqrt(s * (s - a) * (s - b) * (s - c));
    }
}
""", "Shapes.cs")}
{C(r"""
List<Shape> shapes = [ new Circle(2), new Rectangle(3, 4), new Triangle(3, 4, 5) ];

foreach (Shape s in shapes)
    Console.WriteLine(s.Describe());        // each object runs ITS OWN Area()

// Circle    area    12.57  perimeter   12.57
// Rectangle area    12.00  perimeter   14.00
// Triangle  area     6.00  perimeter   12.00

double total = 0;
foreach (Shape s in shapes) total += s.Area();
Console.WriteLine($"Total area: {total:F2}");   // 30.57

// var x = new Shape("blob");               // ❌ CS0144: cannot create an instance of an abstract class
""")}
{tip("Adding a <code>Hexagon</code> means writing one new class. The loop above doesn't change. That's the Open/Closed Principle you'll formalise in Week 9.")}

<h3>3. Template Method: a real-world abstract class</h3>
<p>Payment flows share the same steps (validate amount, run checks, charge, add fees) but each method does the specifics differently. The base class owns the algorithm; subclasses fill in the blanks.</p>
{C(r"""
public record PaymentResult(bool Success, string? Reference, decimal Charged, string? Error)
{
    public static PaymentResult Ok(string reference, decimal charged) => new(true, reference, charged, null);
    public static PaymentResult Fail(string error) => new(false, null, 0, error);
}

public abstract class PaymentProcessor
{
    // Template method: NOT virtual — the order of steps is fixed
    public PaymentResult Process(decimal amount)
    {
        if (amount <= 0) return PaymentResult.Fail("Amount must be positive");
        if (!Validate(amount)) return PaymentResult.Fail($"{Method} rejected {amount:N2}");

        string reference = Charge(amount);
        return PaymentResult.Ok(reference, amount + Fee(amount));
    }

    protected abstract string Method { get; }               // required
    protected abstract bool Validate(decimal amount);       // required
    protected abstract string Charge(decimal amount);       // required
    protected virtual decimal Fee(decimal amount) => 0m;    // optional hook
}

public class UpiProcessor : PaymentProcessor
{
    protected override string Method => "UPI";
    protected override bool Validate(decimal amount) => amount <= 100_000m;     // typical per-transaction cap
    protected override string Charge(decimal amount) => "UPI-" + Guid.NewGuid().ToString("N")[..10];
}

public class CardProcessor : PaymentProcessor
{
    protected override string Method => "Card";
    protected override bool Validate(decimal amount) => true;
    protected override string Charge(decimal amount) => "CARD-" + Random.Shared.Next(100_000, 999_999);
    protected override decimal Fee(decimal amount) => Math.Round(amount * 0.02m, 2);   // 2% fee
}
""", "Payments.cs")}
{C(r"""
PaymentProcessor[] processors = [ new UpiProcessor(), new CardProcessor() ];

foreach (var p in processors)
{
    var r = p.Process(150_000m);
    Console.WriteLine(r.Success ? $"✓ {r.Reference} charged {r.Charged:N2}" : $"✗ {r.Error}");
}
// ✗ UPI rejected 150,000.00
// ✓ CARD-482913 charged 153,000.00
""")}

<h3>4. Type checks and casting</h3>
<p>Sometimes you genuinely need subtype-specific data. Use pattern matching, not blind casts.</p>
{C(r"""
Shape shape = new Circle(12);

// Upcast: implicit, always safe
Shape s1 = new Rectangle(2, 2);

// Downcast with a cast: throws InvalidCastException if wrong
var r = (Rectangle)s1;

// `as`: returns null instead of throwing (reference types only)
Circle? maybe = s1 as Circle;               // null

// `is` with a declaration pattern: test + cast in one step  ✓ preferred
if (shape is Circle c)
    Console.WriteLine($"Radius {c.Radius}");

// switch expression on type + property patterns
string Label(Shape s) => s switch
{
    Circle { Radius: > 10 }                     => "Large circle",
    Circle                                      => "Circle",
    Rectangle rect when rect.Width == rect.Height => "Square",
    Rectangle                                   => "Rectangle",
    _                                           => "Other shape"
};

Console.WriteLine(Label(shape));                   // Large circle
Console.WriteLine(Label(new Rectangle(5, 5)));     // Square
""")}
{warn("If you find yourself writing <code>if (x is A) … else if (x is B) …</code> to choose <i>behaviour</i>, that behaviour probably belongs in a virtual method on the base type.", "Smell")}

<h3>5. Operator overloading (compile-time polymorphism)</h3>
{C(r"""
public readonly struct Money(decimal amount, string currency)
{
    public decimal Amount { get; } = amount;
    public string Currency { get; } = currency;

    public static Money operator +(Money a, Money b)
    {
        if (a.Currency != b.Currency)
            throw new InvalidOperationException($"Can't add {a.Currency} and {b.Currency}");
        return new Money(a.Amount + b.Amount, a.Currency);
    }

    public static Money operator *(Money m, int qty) => new(m.Amount * qty, m.Currency);

    public override string ToString() => $"{Amount:N2} {Currency}";
}

var price = new Money(499m, "INR");
var shipping = new Money(60m, "INR");
Console.WriteLine(price * 3 + shipping);   // 1,557.00 INR
""", "Money.cs")}
''',
["Making a base class concrete when no instance of it should exist — make it abstract.",
"Type-checking chains instead of virtual methods.",
"Using a direct cast where the type might be different — use <code>is</code>.",
"Making the template method itself virtual, so subclasses can break the algorithm.",
"Overloading operators with surprising meanings (+ that subtracts, == that ignores key fields)."],
("40 min", ["Add <code>Hexagon(side)</code> to the shapes and print all four sorted by area.",
"Write abstract <code>Notification</code> with a template method <code>Send(to, message)</code>: validate recipient → format → deliver. Implement <code>EmailNotification</code> and <code>SmsNotification</code> (SMS truncates to 160 chars).",
"Use a switch expression with type patterns to print an icon per notification type."]),
[("Can an abstract class have a constructor?","Yes, usually <code>protected</code>. It runs when a derived class is constructed and initialises shared state."),
("Can an abstract class have no abstract members?","Yes. It then just can't be instantiated directly, which is useful for a base that only makes sense through subclasses."),
("What's the safest way to downcast?","Pattern matching: <code>if (obj is Circle c) { ... }</code>. It tests and casts in one step and never throws.")],
[("Basic","What is polymorphism? Give an example.","The ability of one interface to work with objects of different types, with each type supplying its own behaviour. Example: a <code>List&lt;Shape&gt;</code> where calling <code>Area()</code> runs the Circle, Rectangle or Triangle implementation depending on each object's actual type."),
("Basic","Differentiate compile-time and runtime polymorphism.","Compile-time (static) polymorphism is overloading: the compiler picks the method from the argument types. Runtime (dynamic) polymorphism is overriding: the CLR picks the implementation from the object's runtime type via virtual dispatch."),
("Basic","What is an abstract class? Can you instantiate one?","A class declared abstract that may contain both implemented and abstract members. It can't be instantiated; it serves as a base that derived classes complete."),
("Intermediate","What is the Template Method pattern?","A base class defines an algorithm's skeleton in a non-virtual method and calls abstract or virtual steps that subclasses implement. The structure stays fixed while details vary. Examples: payment processors, report generators, and .NET's <code>BackgroundService</code>, whose <code>StartAsync</code> calls the abstract <code>ExecuteAsync</code> you override."),
("Intermediate","How does virtual dispatch work under the hood?","Each type has a method table (vtable) with slots for virtual methods. An override replaces the slot in the derived type's table. A virtual call loads the object's method table pointer and jumps to the slot, so the most-derived implementation runs."),
("Intermediate","What's the difference between is, as and a direct cast?","A cast <code>(T)x</code> throws InvalidCastException on failure. <code>as</code> returns null on failure and works only with reference/nullable types. <code>is</code> returns a bool and, with a declaration pattern (<code>x is T t</code>), also gives you the typed variable. Prefer the pattern form.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Interfaces, default interface methods, interface vs abstract class",
"Define contracts with interfaces, program against them instead of concrete classes, and choose correctly between an interface and an abstract class.",
[("Interface","A named contract listing members a type promises to implement, with no instance state."),
("Implement","A class or struct provides bodies for all of an interface's members: <code>class EmailSender : INotificationSender</code>."),
("Programming to an interface","Depending on the contract (<code>INotificationSender</code>) rather than a concrete class (<code>EmailSender</code>)."),
("Dependency injection (DI)","Passing a class its dependencies (usually as interfaces) from outside, typically through the constructor."),
("Loose coupling","Classes know as little as possible about each other's concrete types, so either side can change independently."),
("Explicit implementation","Implementing a member as <code>void IFoo.Run()</code>; it's only callable through the interface."),
("Default interface method","C# 8 feature letting an interface member have a body that implementers inherit."),
("Static abstract member","C# 11 feature letting interfaces require static members, used for generic math."),
("Marker interface","An interface with no members used to tag types (prefer attributes in modern .NET)."),
("IComparable&lt;T&gt;","Built-in interface defining a type's natural sort order via CompareTo."),
("IDisposable","Built-in interface with Dispose() for releasing unmanaged or expensive resources; used by <code>using</code>."),
("Fake / test double","A simple implementation of an interface used in tests instead of the real thing.")],
["An interface says <i>what</i>, a class says <i>how</i>.",
"A class can inherit one class but implement many interfaces.",
"Depend on interfaces in constructors; this is the foundation of ASP.NET Core's DI container.",
"Name interfaces with an I prefix and an ability or role: <code>IRepository</code>, <code>IComparable</code>.",
"Keep interfaces small and focused (Interface Segregation).",
"Abstract class = shared code + is-a; interface = capability/contract, no state."],
f'''
<h3>1. Defining and implementing an interface</h3>
{C(r"""
public interface INotificationSender
{
    string Channel { get; }
    bool Send(string to, string message);
}

public class EmailSender : INotificationSender
{
    public string Channel => "Email";
    public bool Send(string to, string message)
    {
        if (!to.Contains('@')) return false;
        Console.WriteLine($"[Email → {to}] {message}");
        return true;
    }
}

public class SmsSender : INotificationSender
{
    public string Channel => "SMS";
    public bool Send(string to, string message)
    {
        if (to.Length != 10 || !to.All(char.IsDigit)) return false;
        string body = message.Length > 160 ? message[..157] + "..." : message;
        Console.WriteLine($"[SMS → {to}] {body}");
        return true;
    }
}
""", "Notifications.cs")}

<h3>2. Programming to an interface (DI by hand)</h3>
<p><code>OrderService</code> doesn't know or care whether it's emailing or texting. It depends on the contract only, and receives the implementation through its constructor.</p>
{C(r"""
public class OrderService
{
    private readonly INotificationSender _notifier;

    public OrderService(INotificationSender notifier) => _notifier = notifier;   // injected

    public void PlaceOrder(int orderId, string customerContact)
    {
        // ... save the order ...
        bool sent = _notifier.Send(customerContact, $"Order #{orderId} confirmed. Thank you!");
        Console.WriteLine(sent ? $"Notified via {_notifier.Channel}" : "Notification failed");
    }
}

// Composition root: the ONE place that picks concrete classes
var byEmail = new OrderService(new EmailSender());
byEmail.PlaceOrder(501, "asha@example.com");

var bySms = new OrderService(new SmsSender());
bySms.PlaceOrder(502, "9876543210");
""", "OrderService.cs")}
<p>In tests, swap in a fake that records what was sent, with no real email involved:</p>
{C(r"""
public class FakeSender : INotificationSender
{
    public List<string> Sent { get; } = new();
    public string Channel => "Fake";
    public bool Send(string to, string message) { Sent.Add($"{to}: {message}"); return true; }
}

var fake = new FakeSender();
new OrderService(fake).PlaceOrder(1, "test");
Console.WriteLine(fake.Sent.Count);   // 1  ← assert this in a unit test (Week 39)
""")}
{tip("In ASP.NET Core (Week 17) you'll register <code>builder.Services.AddScoped&lt;INotificationSender, EmailSender&gt;();</code> and the framework does this wiring for you.")}

<h3>3. Multiple interfaces and explicit implementation</h3>
{C(r"""
public interface IPrintable  { void Print(); }
public interface IExportable { byte[] Export(string format); }

public class Invoice : IPrintable, IExportable          // one class, many contracts
{
    public void Print() => Console.WriteLine("Printing invoice...");
    public byte[] Export(string format) => System.Text.Encoding.UTF8.GetBytes($"invoice as {format}");
}

// When two interfaces have the same member, implement them explicitly
public interface IFileLogger    { void Write(string message); }
public interface IConsoleLogger { void Write(string message); }

public class DualLogger : IFileLogger, IConsoleLogger
{
    void IFileLogger.Write(string message)    => File.AppendAllText("app.log", message + Environment.NewLine);
    void IConsoleLogger.Write(string message) => Console.WriteLine(message);
}

var logger = new DualLogger();
// logger.Write("x");                         // ❌ not visible on the class itself
((IConsoleLogger)logger).Write("to console");
IFileLogger fileLog = logger;
fileLog.Write("to file");
""")}

<h3>4. Built-in interfaces you'll use constantly</h3>
{C(r"""
public class Student : IComparable<Student>
{
    public required string Name { get; init; }
    public double Cgpa { get; init; }

    // Natural order: highest CGPA first
    public int CompareTo(Student? other) => other is null ? 1 : other.Cgpa.CompareTo(Cgpa);   // by convention any instance > null
    public override string ToString() => $"{Name} ({Cgpa})";
}

var batch = new List<Student>
{
    new() { Name = "Neha",  Cgpa = 8.4 },
    new() { Name = "Rohit", Cgpa = 9.1 },
    new() { Name = "Imran", Cgpa = 7.9 }
};
batch.Sort();                                   // uses CompareTo
Console.WriteLine(string.Join(", ", batch));    // Rohit (9.1), Neha (8.4), Imran (7.9)
""", "Student.cs")}
{C(r"""
public sealed class ReportWriter : IDisposable
{
    private readonly StreamWriter _writer;
    public ReportWriter(string path) => _writer = new StreamWriter(path);
    public void Line(string text) => _writer.WriteLine(text);
    public void Dispose()
    {
        _writer.Dispose();
        Console.WriteLine("Report file closed");
    }
}

using (var report = new ReportWriter("q3.txt"))   // Dispose() runs at the closing brace,
{                                                 // even if an exception is thrown
    report.Line("Q3 revenue: 42,00,000");
}
""", "ReportWriter.cs")}
{table(["Interface","Purpose","You'll meet it in"],[
["<code>IEnumerable&lt;T&gt;</code>","Can be iterated with foreach / LINQ","Weeks 4–5"],
["<code>IComparable&lt;T&gt;</code>, <code>IComparer&lt;T&gt;</code>","Sorting","Week 4"],
["<code>IEquatable&lt;T&gt;</code>","Type-safe equality","Week 4"],
["<code>IDisposable</code> / <code>IAsyncDisposable</code>","Resource cleanup","Week 6"],
["<code>ILogger&lt;T&gt;</code>","Logging abstraction","Weeks 6, 19"]])}

<h3>5. Default interface methods (C# 8)</h3>
<p>An interface member can have a body. Implementers get it for free and may override it. The main use is evolving a published interface without breaking existing implementations.</p>
{C(r"""
public interface IDiscountPolicy
{
    decimal Rate { get; }
    decimal Apply(decimal amount) => Math.Round(amount - amount * Rate, 2);   // default body
}

public class FestiveDiscount : IDiscountPolicy { public decimal Rate => 0.20m; }

public class LoyaltyDiscount : IDiscountPolicy
{
    public decimal Rate => 0.10m;
    public decimal Apply(decimal amount) => amount >= 5_000m ? amount * 0.85m : amount * 0.90m; // own version
}

IDiscountPolicy festive = new FestiveDiscount();
Console.WriteLine(festive.Apply(1_000m));        // 800.00

// var f = new FestiveDiscount(); f.Apply(1000);  // ❌ default members are only reachable via the interface
""")}
{warn("Default methods can't access instance fields (interfaces have none). Don't use them to turn interfaces into abstract classes.", "Limit")}
<p>C# 11 also added <b>static abstract</b> interface members (<code>static abstract T Zero {{ get; }}</code>), which power generic math like <code>INumber&lt;T&gt;</code>. Awareness is enough for now.</p>

<h3>6. Interface vs abstract class</h3>
{table(["","Interface","Abstract class"],[
["Inheritance","A class can implement many","A class can inherit only one"],
["State (fields)","No instance fields","Yes"],
["Constructors","No","Yes"],
["Member access","Public by default","Any access modifier"],
["Implementation","Optional defaults (C# 8+)","Full shared implementation"],
["Relationship","\"can do\" / capability","\"is a\" / shared identity"],
["Versioning","Adding members can break implementers (unless default)","Adding non-abstract members is safe"],
["Works with structs","Yes","No"]])}
<h4>Decision guide</h4>
<ul>
<li>Need a contract that unrelated types can fulfil, or need to mock it in tests → <b>interface</b>.</li>
<li>Several closely related types share real code and state → <b>abstract class</b>.</li>
<li>Both at once is common: <code>abstract class PaymentProcessor : IPaymentProcessor</code>. Consumers depend on the interface; implementers reuse the base class.</li>
</ul>
''',
["Creating an interface for every class \"just because\". Add one when you have two implementations or need to test against it.",
"Fat interfaces with 15 members that most implementers only half-support.",
"Newing up concrete dependencies inside a class (<code>new EmailSender()</code>) instead of injecting them.",
"Expecting default interface members to be callable on the class type.",
"Forgetting <code>using</code> on IDisposable objects, which leaks file handles and connections."],
("40 min", ["Create <code>IShippingCalculator</code> with <code>decimal Calculate(decimal weightKg, string pinCode)</code> and two implementations: <code>FlatRateShipping</code> and <code>WeightBasedShipping</code>.",
"Write <code>CheckoutService</code> that takes the interface in its constructor and prints the total for a cart. Swap implementations in Program.cs.",
"Make <code>Product</code> implement <code>IComparable&lt;Product&gt;</code> by price and sort a list."]),
[("Can an interface contain fields?","No instance fields. Since C# 8 it can contain static fields, static methods, default method bodies and constants."),
("Why prefer constructor injection?","Dependencies are explicit, required at creation, easy to replace with fakes in tests, and the object is fully usable as soon as it's constructed."),
("When is explicit interface implementation useful?","When two interfaces declare the same member, or when you want to hide a member from the class's public surface (e.g. a rarely used <code>IDisposable.Dispose</code> exposed as <code>Close()</code>).")],
[("Basic","What is an interface and why do we use it?","An interface is a contract of members that implementing types must provide. It enables polymorphism across unrelated types, loose coupling, multiple 'inheritance' of contracts, dependency injection and mocking in unit tests."),
("Basic","Interface vs abstract class — when would you use each?","Use an interface to define a capability that many unrelated types can implement, or for DI and testing. Use an abstract class when related types share state and implementation and form a clear is-a hierarchy. A class can implement many interfaces but inherit only one class."),
("Basic","Can a class implement multiple interfaces? What if two have the same method?","Yes. If signatures clash and behaviour should differ, use explicit implementation (<code>void IA.Run()</code>); otherwise one public method satisfies both."),
("Intermediate","What are default interface methods and why were they added?","C# 8 lets interface members have implementations. They were added so library authors can add members to published interfaces without breaking existing implementations, and for interop with Java/Swift-style traits. They're only callable through the interface type."),
("Intermediate","How do interfaces enable unit testing?","When a class depends on an interface, a test can pass a fake or mock implementation (hand-written or via Moq/NSubstitute), isolating the class from databases, email servers, clocks and other slow or non-deterministic dependencies."),
("Intermediate","What is the Interface Segregation Principle?","Clients shouldn't be forced to depend on methods they don't use. Prefer several small, focused interfaces (IReader, IWriter) over one large one, so implementers aren't forced to throw NotImplementedException.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project 2: Library management system (models and interfaces)",
"Design the domain model of a library with an abstract base class, three item types, members, and interfaces for searching and storage. Budget: about 4 hours.",
[("Domain model","Classes that represent the real-world business concepts (items, members, loans) and their rules."),
("Catalog","The collection of all items and members, hidden behind the <code>ICatalog</code> interface."),
("In-memory repository","An implementation that stores data in lists; later replaced by a database (Week 15) without changing callers."),
("Seed data","Sample records loaded at startup so the app is usable immediately.")],
["LibraryItem is abstract: there's no such thing as a plain \"item\" on the shelf.",
"Each subtype answers its own LoanDays, Kind and late fee — polymorphism, not if/else.",
"Everything searchable implements ISearchable, so search can cover books and members alike.",
"Program.cs depends on ICatalog, not InMemoryCatalog.",
"<code>IsAvailable</code> has an internal setter: only Core can change it."],
f'''
<h3>Requirements</h3>
<ul>
<li>Item types: <b>Book</b> (author, ISBN, 14-day loan, ₹5/day late fee), <b>Magazine</b> (issue no., 7 days, ₹2/day), <b>DVD</b> (runtime, 3 days, ₹10/day).</li>
<li>Members with auto-generated ids, unique email, max 3 loans at a time.</li>
<li>Menu: list items, add book, add member, list members, exit.</li>
<li>Logic and models in <code>Library.Core</code>; console I/O in <code>Library.App</code>.</li>
<li>Tomorrow: borrow, return, late fees and search.</li>
</ul>

<h3>Class design</h3>
<pre class="mermaid">
classDiagram
  class ISearchable {{ <<interface>> +Matches(term) bool }}
  class LibraryItem {{ <<abstract>> +Id +Title +Year +IsAvailable +LoanDays* +Kind* +LateFeePerDay }}
  class Book {{ +Author +Isbn }}
  class Magazine {{ +IssueNumber }}
  class Dvd {{ +RuntimeMinutes }}
  class Member {{ +Id +Name +Email +MaxLoans }}
  class ICatalog {{ <<interface>> +AddItem() +AddMember() +FindItem() +FindMember() }}
  class InMemoryCatalog
  ISearchable <|.. LibraryItem
  ISearchable <|.. Member
  LibraryItem <|-- Book
  LibraryItem <|-- Magazine
  LibraryItem <|-- Dvd
  ICatalog <|.. InMemoryCatalog
  InMemoryCatalog o-- LibraryItem
  InMemoryCatalog o-- Member
</pre>

<h3>Scaffold</h3>
{C(r"""
dotnet new sln -n Library
dotnet new classlib -n Library.Core
dotnet new console  -n Library.App
dotnet sln add Library.Core Library.App
dotnet add Library.App reference Library.Core
dotnet new gitignore
rm Library.Core/Class1.cs
""", lang="bash")}
{C(r"""
Library/
├─ Library.sln
├─ Library.Core/
│  ├─ Interfaces/
│  │  ├─ ISearchable.cs
│  │  └─ ICatalog.cs
│  ├─ Models/
│  │  ├─ LibraryItem.cs
│  │  ├─ Book.cs
│  │  ├─ Magazine.cs
│  │  ├─ Dvd.cs
│  │  └─ Member.cs
│  └─ Services/
│     ├─ InMemoryCatalog.cs
│     └─ SeedData.cs
└─ Library.App/
   ├─ ConsoleInput.cs
   └─ Program.cs
""", lang="text")}

<h3>Step 1 — Interfaces</h3>
{C(r"""
namespace Library.Core.Interfaces;

public interface ISearchable
{
    bool Matches(string term);
}
""", "Library.Core/Interfaces/ISearchable.cs")}
{C(r"""
using Library.Core.Models;

namespace Library.Core.Interfaces;

public interface ICatalog
{
    IReadOnlyList<LibraryItem> Items { get; }
    IReadOnlyList<Member> Members { get; }

    void AddItem(LibraryItem item);
    void AddMember(Member member);
    LibraryItem? FindItem(int id);
    Member? FindMember(int id);
}
""", "Library.Core/Interfaces/ICatalog.cs")}

<h3>Step 2 — The abstract base item</h3>
{C(r"""
using Library.Core.Interfaces;

namespace Library.Core.Models;

public abstract class LibraryItem : ISearchable
{
    private static int _nextId = 1;

    public int Id { get; }
    public string Title { get; }
    public int Year { get; }
    public bool IsAvailable { get; internal set; } = true;   // only Library.Core can change it

    protected LibraryItem(string title, int year)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(title);
        if (year < 1450 || year > DateTime.Today.Year)
            throw new ArgumentOutOfRangeException(nameof(year), $"Year must be between 1450 and {DateTime.Today.Year}");

        Id = _nextId++;
        Title = title.Trim();
        Year = year;
    }

    public abstract int LoanDays { get; }        // every type MUST decide
    public abstract string Kind { get; }
    public virtual decimal LateFeePerDay => 5m;  // sensible default, may override

    public virtual bool Matches(string term) =>
        Title.Contains(term, StringComparison.OrdinalIgnoreCase);

    public override string ToString() =>
        $"#{Id,-3} {Kind,-8} {Title} ({Year})  [{(IsAvailable ? "available" : "on loan")}]";
}
""", "Library.Core/Models/LibraryItem.cs")}

<h3>Step 3 — Concrete item types</h3>
{C(r"""
namespace Library.Core.Models;

public class Book : LibraryItem
{
    public string Author { get; }
    public string Isbn { get; }

    public Book(string title, string author, int year, string isbn) : base(title, year)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(author);
        string digits = isbn.Replace("-", "").Trim();
        if (digits.Length is not (10 or 13))
            throw new ArgumentException("ISBN must have 10 or 13 digits", nameof(isbn));

        Author = author.Trim();
        Isbn = digits;
    }

    public override int LoanDays => 14;
    public override string Kind => "Book";

    // Extend the base search: title OR author OR exact ISBN
    public override bool Matches(string term) =>
        base.Matches(term)
        || Author.Contains(term, StringComparison.OrdinalIgnoreCase)
        || Isbn == term.Replace("-", "");

    public override string ToString() => $"{base.ToString()}  by {Author}";
}
""", "Library.Core/Models/Book.cs")}
{C(r"""
namespace Library.Core.Models;

public class Magazine(string title, int year, int issueNumber) : LibraryItem(title, year)
{
    public int IssueNumber { get; } = issueNumber > 0
        ? issueNumber
        : throw new ArgumentOutOfRangeException(nameof(issueNumber));

    public override int LoanDays => 7;
    public override string Kind => "Magazine";
    public override decimal LateFeePerDay => 2m;

    public override string ToString() => $"{base.ToString()}  issue {IssueNumber}";
}
""", "Library.Core/Models/Magazine.cs")}
{C(r"""
namespace Library.Core.Models;

public class Dvd(string title, int year, int runtimeMinutes) : LibraryItem(title, year)
{
    public int RuntimeMinutes { get; } = runtimeMinutes > 0
        ? runtimeMinutes
        : throw new ArgumentOutOfRangeException(nameof(runtimeMinutes));

    public override int LoanDays => 3;
    public override string Kind => "DVD";
    public override decimal LateFeePerDay => 10m;

    public override string ToString() => $"{base.ToString()}  {RuntimeMinutes} min";
}
""", "Library.Core/Models/Dvd.cs")}

<h3>Step 4 — Member</h3>
{C(r"""
using Library.Core.Interfaces;

namespace Library.Core.Models;

public class Member : ISearchable
{
    private static int _nextId = 1001;
    public const int MaxLoans = 3;

    public int Id { get; }
    public string Name { get; }
    public string Email { get; }
    public DateOnly JoinedOn { get; } = DateOnly.FromDateTime(DateTime.Today);

    public Member(string name, string email)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        if (string.IsNullOrWhiteSpace(email) || !email.Contains('@') || email.StartsWith('@'))
            throw new ArgumentException("A valid email is required", nameof(email));

        Id = _nextId++;
        Name = name.Trim();
        Email = email.Trim().ToLowerInvariant();
    }

    public bool Matches(string term) =>
        Name.Contains(term, StringComparison.OrdinalIgnoreCase)
        || Email.Contains(term, StringComparison.OrdinalIgnoreCase);

    public override string ToString() => $"M{Id}  {Name}  <{Email}>  since {JoinedOn:dd MMM yyyy}";
}
""", "Library.Core/Models/Member.cs")}

<h3>Step 5 — In-memory catalog and seed data</h3>
<p>The <code>Any</code> and <code>FirstOrDefault</code> calls below are LINQ (Week 5). For now read them as "is there any item where…" and "the first item where…, or null".</p>
{C(r"""
using Library.Core.Interfaces;
using Library.Core.Models;

namespace Library.Core.Services;

public class InMemoryCatalog : ICatalog
{
    private readonly List<LibraryItem> _items = [];
    private readonly List<Member> _members = [];

    public IReadOnlyList<LibraryItem> Items => _items.AsReadOnly();
    public IReadOnlyList<Member> Members => _members.AsReadOnly();

    public void AddItem(LibraryItem item)
    {
        ArgumentNullException.ThrowIfNull(item);
        if (item is Book book && _items.OfType<Book>().Any(b => b.Isbn == book.Isbn))
            throw new InvalidOperationException($"A book with ISBN {book.Isbn} already exists");
        _items.Add(item);
    }

    public void AddMember(Member member)
    {
        ArgumentNullException.ThrowIfNull(member);
        if (_members.Any(m => m.Email == member.Email))
            throw new InvalidOperationException($"{member.Email} is already registered");
        _members.Add(member);
    }

    public LibraryItem? FindItem(int id) => _items.FirstOrDefault(i => i.Id == id);
    public Member? FindMember(int id) => _members.FirstOrDefault(m => m.Id == id);
}
""", "Library.Core/Services/InMemoryCatalog.cs")}
{C(r"""
using Library.Core.Interfaces;
using Library.Core.Models;

namespace Library.Core.Services;

public static class SeedData
{
    public static void Load(ICatalog catalog)
    {
        catalog.AddItem(new Book("Clean Code", "Robert C. Martin", 2008, "978-0132350884"));
        catalog.AddItem(new Book("The Pragmatic Programmer", "David Thomas, Andrew Hunt", 2019, "978-0135957059"));
        catalog.AddItem(new Book("Designing Data-Intensive Applications", "Martin Kleppmann", 2017, "978-1449373320"));
        catalog.AddItem(new Magazine("Digit", 2026, 11));
        catalog.AddItem(new Dvd("3 Idiots", 2009, 170));

        catalog.AddMember(new Member("Samrath", "samrath@example.com"));
        catalog.AddMember(new Member("Ananya Rao", "ananya@example.com"));
    }
}
""", "Library.Core/Services/SeedData.cs")}

<h3>Step 6 — Console app</h3>
<p>Copy <code>ConsoleInput.cs</code> from Week 1 (namespace <code>Library.App</code>) and add a text reader:</p>
{C(r"""
public static string ReadText(string prompt)
{
    while (true)
    {
        Console.Write(prompt);
        string? text = Console.ReadLine();
        if (text is null) Environment.Exit(0);
        if (!string.IsNullOrWhiteSpace(text)) return text.Trim();
        Console.WriteLine("  ✗ This field is required.");
    }
}

public static int ReadInt(string prompt, int min, int max) => ReadChoice(prompt, min, max);
""", "Library.App/ConsoleInput.cs (add these)")}
{C(r"""
using Library.App;
using Library.Core.Interfaces;
using Library.Core.Models;
using Library.Core.Services;

ICatalog catalog = new InMemoryCatalog();     // depend on the interface
SeedData.Load(catalog);

int choice;
do
{
    Console.WriteLine(QQQ

        ===== City Library =====
        1) List items
        2) Add book
        3) Add member
        4) List members
        0) Exit
        QQQ);
    choice = ConsoleInput.ReadChoice("Choose: ", 0, 4);

    try
    {
        switch (choice)
        {
            case 1: ListItems(); break;
            case 2: AddBook(); break;
            case 3: AddMember(); break;
            case 4: ListMembers(); break;
        }
    }
    catch (ArgumentException ex)          { Console.WriteLine($"  ✗ {ex.Message}"); }
    catch (InvalidOperationException ex)  { Console.WriteLine($"  ✗ {ex.Message}"); }
} while (choice != 0);

void ListItems()
{
    foreach (LibraryItem item in catalog.Items)
        Console.WriteLine($"  {item}");          // each subtype's own ToString()
}

void AddBook()
{
    string title  = ConsoleInput.ReadText("Title: ");
    string author = ConsoleInput.ReadText("Author: ");
    int year      = ConsoleInput.ReadInt("Year: ", 1450, DateTime.Today.Year);
    string isbn   = ConsoleInput.ReadText("ISBN: ");

    var book = new Book(title, author, year, isbn);
    catalog.AddItem(book);
    Console.WriteLine($"  ✓ Added {book}");
}

void AddMember()
{
    string name  = ConsoleInput.ReadText("Name: ");
    string email = ConsoleInput.ReadText("Email: ");
    var member = new Member(name, email);
    catalog.AddMember(member);
    Console.WriteLine($"  ✓ Registered {member}");
}

void ListMembers()
{
    foreach (Member m in catalog.Members)
        Console.WriteLine($"  {m}");
}
""", "Library.App/Program.cs")}

<h3>Run it</h3>
{C(r"""
$ dotnet run --project Library.App
Choose: 1
  #1   Book     Clean Code (2008)  [available]  by Robert C. Martin
  #2   Book     The Pragmatic Programmer (2019)  [available]  by David Thomas, Andrew Hunt
  #3   Book     Designing Data-Intensive Applications (2017)  [available]  by Martin Kleppmann
  #4   Magazine Digit (2026)  [available]  issue 11
  #5   DVD      3 Idiots (2009)  [available]  170 min
""", lang="text")}

<h3>Stretch goals</h3>
<ul>
<li>Add menu options for adding a magazine and a DVD.</li>
<li>Add an <code>AudioBook : Book</code> with narrator and a 21-day loan. Did any existing code need to change?</li>
<li>Validate ISBN-13 checksums properly.</li>
</ul>
''',
iqs=[("Basic","Why is LibraryItem abstract rather than concrete?","No real item is just a 'library item'; every one is a book, magazine or DVD. Making it abstract prevents meaningless instances and forces each subtype to define LoanDays and Kind."),
("Basic","Why does Program.cs declare ICatalog instead of InMemoryCatalog?","So the app depends on the contract only. Replacing storage with a database later (Week 15) means writing a new ICatalog implementation and changing one line, not the whole app."),
("Intermediate","Why is IsAvailable's setter internal?","Only the domain/service layer in Library.Core should change availability, through borrow/return rules. internal blocks the console app or any other assembly from flipping it directly and bypassing those rules."),
("Intermediate","How would you add a new item type without modifying existing code?","Create a new class deriving from LibraryItem and override the abstract members. Listing, searching and (tomorrow) borrowing all work through the base type, so nothing else changes. That's the Open/Closed Principle.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Borrow, return and search, plus README, push and revision",
"Add the business rules (loans, due dates, late fees, search), make time testable with an interface, document the project, and revise the week.",
[("Business rule","A constraint from the real domain, e.g. a member may hold at most 3 items."),
("Service class","A class that coordinates domain objects to carry out a use case (LibraryService.Borrow)."),
("Result object","A return type that carries success/failure and an error message instead of throwing for expected failures."),
("Clock abstraction","An interface like <code>IClock</code> that supplies the current date, so tests can control time."),
("DateOnly","A .NET 6+ type for a calendar date without a time; ideal for due dates.")],
["Rules live in the service and domain classes, never in Program.cs.",
"Expected failures (item on loan, limit reached) return a Result; programming errors throw.",
"Inject time through <code>IClock</code> so late fees can be tested without waiting two weeks.",
"Search works over <code>ISearchable</code>, so books and members are found by one method.",
"Revise by explaining aloud; re-read anything you can't explain."],
f'''
<h3>1. Make time injectable</h3>
<p>Late fees depend on today's date. If the code calls <code>DateTime.Today</code> directly, you can't test a late return. Put time behind an interface.</p>
{C(r"""
namespace Library.Core.Interfaces;

public interface IClock
{
    DateOnly Today { get; }
}
""", "Library.Core/Interfaces/IClock.cs")}
{C(r"""
using Library.Core.Interfaces;

namespace Library.Core.Services;

public class SystemClock : IClock
{
    public DateOnly Today => DateOnly.FromDateTime(DateTime.Today);
}

// A clock you control — perfect for demos and tests
public class ManualClock(DateOnly start) : IClock
{
    public DateOnly Today { get; private set; } = start;
    public void Advance(int days) => Today = Today.AddDays(days);
}
""", "Library.Core/Services/Clocks.cs")}

<h3>2. Loan and Result</h3>
{C(r"""
namespace Library.Core.Models;

public class Loan
{
    public LibraryItem Item { get; }
    public Member Member { get; }
    public DateOnly BorrowedOn { get; }
    public DateOnly DueOn { get; }
    public DateOnly? ReturnedOn { get; private set; }
    public bool IsOpen => ReturnedOn is null;

    public Loan(LibraryItem item, Member member, DateOnly borrowedOn)
    {
        Item = item;
        Member = member;
        BorrowedOn = borrowedOn;
        DueOn = borrowedOn.AddDays(item.LoanDays);     // polymorphic: 14, 7 or 3 days
    }

    public int DaysOverdue(DateOnly today) => Math.Max(0, today.DayNumber - DueOn.DayNumber);

    // Closes the loan and returns the late fee
    public decimal Close(DateOnly returnedOn)
    {
        if (!IsOpen) throw new InvalidOperationException("Loan is already closed");
        ReturnedOn = returnedOn;
        return DaysOverdue(returnedOn) * Item.LateFeePerDay;   // polymorphic fee
    }

    public override string ToString() =>
        $"{Item.Title} → {Member.Name}, due {DueOn:dd MMM}" + (IsOpen ? "" : $", returned {ReturnedOn:dd MMM}");
}
""", "Library.Core/Models/Loan.cs")}
{C(r"""
namespace Library.Core.Models;

public record Result<T>(bool Success, T? Value, string? Error)
{
    public static Result<T> Ok(T value)      => new(true, value, null);
    public static Result<T> Fail(string why) => new(false, default, why);
}
""", "Library.Core/Models/Result.cs")}

<h3>3. LibraryService — the business rules</h3>
{C(r"""
using Library.Core.Interfaces;
using Library.Core.Models;

namespace Library.Core.Services;

public class LibraryService(ICatalog catalog, IClock clock)
{
    private readonly List<Loan> _loans = [];

    public IReadOnlyList<Loan> OpenLoans => _loans.Where(l => l.IsOpen).ToList();

    public IReadOnlyList<Loan> Overdue => _loans.Where(l => l.IsOpen && l.DaysOverdue(clock.Today) > 0).ToList();

    public Result<Loan> Borrow(int memberId, int itemId)
    {
        Member? member = catalog.FindMember(memberId);
        if (member is null) return Result<Loan>.Fail($"No member with id {memberId}");

        LibraryItem? item = catalog.FindItem(itemId);
        if (item is null) return Result<Loan>.Fail($"No item with id {itemId}");
        if (!item.IsAvailable) return Result<Loan>.Fail($"'{item.Title}' is already on loan");

        int active = _loans.Count(l => l.IsOpen && l.Member.Id == member.Id);
        if (active >= Member.MaxLoans)
            return Result<Loan>.Fail($"{member.Name} already has {Member.MaxLoans} items out");

        if (_loans.Any(l => l.IsOpen && l.Member.Id == member.Id && l.DaysOverdue(clock.Today) > 0))
            return Result<Loan>.Fail($"{member.Name} has an overdue item; return it first");

        var loan = new Loan(item, member, clock.Today);
        item.IsAvailable = false;                 // allowed: same assembly (internal set)
        _loans.Add(loan);
        return Result<Loan>.Ok(loan);
    }

    public Result<decimal> Return(int itemId)
    {
        Loan? loan = _loans.FirstOrDefault(l => l.IsOpen && l.Item.Id == itemId);
        if (loan is null) return Result<decimal>.Fail($"Item {itemId} isn't on loan");

        decimal fee = loan.Close(clock.Today);
        loan.Item.IsAvailable = true;
        return Result<decimal>.Ok(fee);
    }

    // One search over everything that implements ISearchable
    public IReadOnlyList<ISearchable> Search(string term)
    {
        if (string.IsNullOrWhiteSpace(term)) return [];
        var results = new List<ISearchable>();
        foreach (LibraryItem item in catalog.Items) if (item.Matches(term)) results.Add(item);
        foreach (Member member in catalog.Members) if (member.Matches(term)) results.Add(member);
        return results;
    }
}
""", "Library.Core/Services/LibraryService.cs")}

<h3>4. Updated Program.cs</h3>
<p>Uses a <code>ManualClock</code> so you can "fast-forward" days and see late fees. Swap in <code>new SystemClock()</code> for real use.</p>
{C(r"""
using Library.App;
using Library.Core.Interfaces;
using Library.Core.Models;
using Library.Core.Services;

ICatalog catalog = new InMemoryCatalog();
SeedData.Load(catalog);
var clock = new ManualClock(DateOnly.FromDateTime(DateTime.Today));
var library = new LibraryService(catalog, clock);

int choice;
do
{
    Console.WriteLine($QQQ

        ===== City Library =====  today: {clock.Today:ddd dd MMM yyyy}
        1) List items        5) Borrow
        2) Add book          6) Return
        3) Add member        7) Search
        4) List members      8) Open / overdue loans
        9) Advance days (demo)
        0) Exit
        QQQ);
    choice = ConsoleInput.ReadChoice("Choose: ", 0, 9);

    try
    {
        switch (choice)
        {
            case 1: foreach (var i in catalog.Items) Console.WriteLine($"  {i}"); break;
            case 2: AddBook(); break;
            case 3: AddMember(); break;
            case 4: foreach (var m in catalog.Members) Console.WriteLine($"  {m}"); break;
            case 5: Borrow(); break;
            case 6: Return(); break;
            case 7: Search(); break;
            case 8: ShowLoans(); break;
            case 9: clock.Advance(ConsoleInput.ReadInt("Days to advance: ", 1, 60)); break;
        }
    }
    catch (ArgumentException ex)         { Console.WriteLine($"  ✗ {ex.Message}"); }
    catch (InvalidOperationException ex) { Console.WriteLine($"  ✗ {ex.Message}"); }
} while (choice != 0);

void Borrow()
{
    int memberId = ConsoleInput.ReadInt("Member id (e.g. 1001): ", 1, int.MaxValue);
    int itemId   = ConsoleInput.ReadInt("Item id: ", 1, int.MaxValue);
    var result = library.Borrow(memberId, itemId);
    Console.WriteLine(result.Success ? $"  ✓ {result.Value}" : $"  ✗ {result.Error}");
}

void Return()
{
    int itemId = ConsoleInput.ReadInt("Item id: ", 1, int.MaxValue);
    var result = library.Return(itemId);
    if (!result.Success) { Console.WriteLine($"  ✗ {result.Error}"); return; }
    Console.WriteLine(result.Value > 0 ? $"  ✓ Returned late. Fee: ₹{result.Value:N2}" : "  ✓ Returned on time");
}

void Search()
{
    string term = ConsoleInput.ReadText("Search for: ");
    var hits = library.Search(term);
    if (hits.Count == 0) { Console.WriteLine("  No matches"); return; }
    foreach (ISearchable hit in hits) Console.WriteLine($"  {hit}");
}

void ShowLoans()
{
    Console.WriteLine("  Open loans:");
    foreach (var l in library.OpenLoans) Console.WriteLine($"    {l}");
    Console.WriteLine("  Overdue:");
    foreach (var l in library.Overdue) Console.WriteLine($"    {l}  ({l.DaysOverdue(clock.Today)} days)");
}

void AddBook()
{
    var book = new Book(ConsoleInput.ReadText("Title: "), ConsoleInput.ReadText("Author: "),
                        ConsoleInput.ReadInt("Year: ", 1450, DateTime.Today.Year), ConsoleInput.ReadText("ISBN: "));
    catalog.AddItem(book);
    Console.WriteLine($"  ✓ Added {book}");
}

void AddMember()
{
    var member = new Member(ConsoleInput.ReadText("Name: "), ConsoleInput.ReadText("Email: "));
    catalog.AddMember(member);
    Console.WriteLine($"  ✓ Registered {member}");
}
""", "Library.App/Program.cs")}

<h3>5. Try to break it</h3>
{table(["Scenario","Expected"],[
["Borrow item 5 twice","\"'3 Idiots' is already on loan\""],
["Member 1001 borrows items 1, 2, 3, then 4","Fourth fails: limit of 3"],
["Borrow DVD, advance 5 days, return","Late by 2 days → ₹20.00"],
["Borrow book, advance 20 days, try to borrow another","Blocked: overdue item"],
["Return an item that isn't on loan","\"Item n isn't on loan\""],
["Member id 9999","\"No member with id 9999\""],
["Add member with an existing email","\"... is already registered\""],
["Add book with ISBN \"12\"","\"ISBN must have 10 or 13 digits\""],
["Search \"martin\"","Clean Code and Designing Data-Intensive Applications"]])}

<h3>6. README</h3>
{C(r"""
# City Library — Console Library Management

Micro-project 2 of my .NET full-stack roadmap (Week 2: OOP).

## Features
- Books, magazines and DVDs with type-specific loan periods and late fees
- Members with a 3-item loan limit; overdue members can't borrow
- Borrow, return with late-fee calculation, unified search
- Time abstraction (`IClock`) to simulate days passing

## Design
- `LibraryItem` abstract base → `Book`, `Magazine`, `Dvd` (polymorphic `LoanDays`, `LateFeePerDay`)
- `ISearchable` implemented by items and members
- `ICatalog` interface with an in-memory implementation (swap for EF Core later)
- `LibraryService` holds business rules and returns `Result<T>` for expected failures

## Run
```bash
dotnet run --project Library.App
```

## What I practised
Classes, properties, constructors, encapsulation, access modifiers, static members,
inheritance, abstract classes, polymorphism, interfaces and dependency injection by hand.
""", "README.md", lang="markdown")}
{C(r"""
git add .
git commit -m "Library: models, catalog, borrow/return with late fees, search"
git push
""", lang="bash")}

<h3>7. Week 2 revision checklist</h3>
<ul>
<li>Class vs object; field vs property; the six property styles</li>
<li>Constructor chaining, primary constructors, required/init</li>
<li>Encapsulation with an example; all access modifiers</li>
<li>Static vs instance; static constructor; const vs static readonly</li>
<li>Constructor order in inheritance; virtual/override/sealed; override vs new</li>
<li>Compile-time vs runtime polymorphism; abstract classes; Template Method</li>
<li>Interfaces, DI by hand, explicit implementation, default interface methods</li>
<li>Interface vs abstract class, and when to choose each</li>
</ul>

<h3>8. Quick quiz — predict the output</h3>
<details><summary>Q1. What prints?</summary>
{C(r"""
class A { public A() => Console.Write("A"); }
class B : A { public B() => Console.Write("B"); }
class C : B { public C() => Console.Write("C"); }
new C();
""")}<b>ABC.</b> Base constructor bodies run first, from the top of the hierarchy down.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
class P { public virtual string Hi() => "P"; public string Bye() => "P"; }
class Q : P { public override string Hi() => "Q"; public new string Bye() => "Q"; }
P x = new Q();
Console.WriteLine(x.Hi() + x.Bye());
""")}<b>QP.</b> Hi is overridden (runtime type Q); Bye is hidden (compile-time type P).</details>
<details><summary>Q3. Does this compile?</summary>
{C(r"""
abstract class Shape { public abstract double Area(); }
class Square : Shape { }
""")}<b>No.</b> CS0534: Square doesn't implement the inherited abstract member Area(). Either implement it or mark Square abstract.</details>
<details><summary>Q4. What prints?</summary>
{C(r"""
class Counter { public static int Count; public Counter() => Count++; }
new Counter(); new Counter(); var c = new Counter();
Console.WriteLine(Counter.Count);
""")}<b>3.</b> The static field is shared by all instances.</details>
<details><summary>Q5. Does this compile?</summary>
{C(r"""
interface IGreeter { string Greet() => "Hello"; }
class Greeter : IGreeter { }
var g = new Greeter();
Console.WriteLine(g.Greet());
""")}<b>No.</b> Default interface members aren't inherited by the class's own surface. Declare <code>IGreeter g = new Greeter();</code> instead.</details>

<div class="note tip"><b>Next week:</b> Modern C# and exceptions — structs, records, tuples, pattern matching in depth, enums, equality and boxing, exceptions, and events, ending with the bank account simulator.</div>
''',
iqs=[("Basic","Why return a Result object instead of throwing an exception when an item is already on loan?","An item being on loan is an expected business outcome, not an error in the program. Exceptions are slower, hide control flow and are meant for exceptional situations. A Result makes the failure explicit in the method signature and forces callers to handle it."),
("Basic","Why inject IClock instead of calling DateTime.Today?","Direct calls to static time make code non-deterministic and hard to test. With IClock, tests and demos can control the date (ManualClock) to verify due dates and late fees instantly."),
("Intermediate","Where should business rules like 'max 3 loans' live, and why?","In the domain/service layer (LibraryService, Member.MaxLoans), not the UI. Then every client — console today, Web API later — enforces the same rules, and the rules can be unit-tested in isolation."),
("Intermediate","How does polymorphism show up in the late-fee calculation?","Loan.Close multiplies days overdue by Item.LateFeePerDay, and DueOn uses Item.LoanDays. Both are virtual/abstract members, so a Book, Magazine or DVD each supply their own values with no if/else on type.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Classes, objects, constructors, properties","Classes &amp; properties","Fields vs properties, init/required, constructor chaining, primary constructors.","2 hrs"),
 (2,"TUE","Encapsulation, access modifiers, static members","Encapsulation &amp; static","Protecting invariants, all access modifiers, static members, const vs readonly.","2 hrs"),
 (3,"WED","Inheritance, base, virtual/override, sealed","Inheritance","Constructor order, overriding vs hiding, System.Object, composition.","2 hrs"),
 (4,"THU","Polymorphism and abstract classes","Polymorphism","Abstract members, Template Method, type patterns, operator overloading.","2 hrs"),
 (5,"FRI","Interfaces and interface vs abstract class","Interfaces","Contracts, DI by hand, explicit implementation, default interface methods.","2 hrs"),
 (6,"SAT","Micro-project 2: Library system","Project: library","Abstract items, members, ISearchable, ICatalog, console menu.","4 hrs"),
 (7,"SUN","Borrow, return, search and revision","Loans &amp; revision","Late fees, IClock, Result&lt;T&gt;, README, quiz.","4 hrs"),
]
build("/home/claude/build/week01.html", "/home/claude/build/week02.html", 2,
      "Week 2 — OOP part 1", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 2 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Micro-project 2"],
      "Object-oriented programming is how almost every .NET codebase is organised. This week you'll learn to model real things as classes, protect their data, share behaviour through inheritance and interfaces, and finish with a working library management system.",
      cards, days)
print("built")
