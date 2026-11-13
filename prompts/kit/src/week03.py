import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Structs, records, tuples and deconstruction",
"Choose between class, struct, record and tuple for a given piece of data, and use with-expressions and deconstruction fluently.",
[("struct","A user-defined value type. Copied on assignment, allocated inline (stack or inside its container), can't inherit."),
("readonly struct","A struct whose fields are all readonly, so it's immutable and the compiler avoids defensive copies."),
("record","A reference type (record class) with compiler-generated value equality, ToString, Deconstruct and with-expression support."),
("Positional record","A record declared with parameters, e.g. <code>record Customer(string Name, string Email)</code>; generates init-only properties."),
("record struct","A value-type record (C# 10). <code>readonly record struct</code> makes it immutable."),
("Value equality","Two instances are equal when their data is equal, not when they are the same object."),
("with-expression","Creates a copy of a record or struct with some properties changed: <code>c with {{ Email = \"x\" }}</code>.".replace("{{","{").replace("}}","}")),
("Non-destructive mutation","Producing a modified copy instead of changing the original."),
("Tuple (ValueTuple)","A lightweight value type grouping values, e.g. <code>(string Name, int Age)</code>."),
("Named tuple elements","Giving tuple fields names instead of Item1/Item2."),
("Deconstruction","Unpacking an object or tuple into separate variables: <code>var (name, age) = person;</code>"),
("Deconstruct method","A method <code>void Deconstruct(out T1 a, out T2 b)</code> that enables deconstruction on any type."),
("Discard","<code>_</code> — ignore a value you don't need while deconstructing or pattern matching.")],
["Class: identity and behaviour. Struct: small immutable value. Record: data with value equality. Tuple: temporary grouping.",
"Keep structs small (≈16 bytes or less) and make them <code>readonly</code>.",
"Records compare by value: two records with the same data are <code>==</code>.",
"Use <code>with</code> to change a copy; the original stays the same.",
"Return a named tuple for quick multi-value results inside a class; use a record when the shape is shared across your code.",
"Deconstruction works on tuples, records and anything with a Deconstruct method."],
f'''
<h3>1. Structs</h3>
<p>A struct is a value type: assignment copies the whole value. Use one for small, immutable values that represent a single concept, like a coordinate, money or a date range.</p>
{C(r"""
public readonly struct GeoPoint
{
    public double Lat { get; }
    public double Lng { get; }

    public GeoPoint(double lat, double lng)
    {
        if (lat is < -90 or > 90) throw new ArgumentOutOfRangeException(nameof(lat));
        if (lng is < -180 or > 180) throw new ArgumentOutOfRangeException(nameof(lng));
        Lat = lat;
        Lng = lng;
    }

    // Haversine distance in km
    public double DistanceTo(GeoPoint other)
    {
        const double R = 6371;
        double dLat = ToRad(other.Lat - Lat), dLng = ToRad(other.Lng - Lng);
        double a = Math.Pow(Math.Sin(dLat / 2), 2) +
                   Math.Cos(ToRad(Lat)) * Math.Cos(ToRad(other.Lat)) * Math.Pow(Math.Sin(dLng / 2), 2);
        return 2 * R * Math.Asin(Math.Sqrt(a));
    }

    private static double ToRad(double deg) => deg * Math.PI / 180;
    public override string ToString() => $"({Lat:F4}, {Lng:F4})";
}
""", "GeoPoint.cs")}
{C(r"""
var bengaluru = new GeoPoint(12.9716, 77.5946);
var mumbai    = new GeoPoint(19.0760, 72.8777);
Console.WriteLine($"{bengaluru.DistanceTo(mumbai):F0} km");   // ≈ 845 km

GeoPoint copy = bengaluru;      // full copy — independent value
GeoPoint empty = default;       // (0, 0): every struct has a zero value that skips your constructor
""")}
{table(["Use a struct when…","Use a class when…"],[
["It represents one small value (≈16 bytes or less)","It has identity or a lifecycle (Customer, Order)"],
["It's immutable","It's mutable or large"],
["You create millions and want to avoid heap allocations","It's shared and passed around a lot"],
["It doesn't need inheritance","You need inheritance or polymorphism"]])}
{warn("Mutable structs cause confusing bugs: changing a copy (e.g. an item pulled from a List) doesn't change the original. Make structs <code>readonly</code>.", "Avoid")}

<h3>2. Records</h3>
<p>Records are built for data. The compiler generates value equality, a readable <code>ToString()</code>, a <code>Deconstruct</code> method and support for <code>with</code>.</p>
{C(r"""
// Positional record: one line gives you a constructor, init-only properties, equality, ToString, Deconstruct
public record Customer(string Name, string Email, string City = "Bengaluru");

var a = new Customer("Asha", "asha@example.com");
var b = new Customer("Asha", "asha@example.com");

Console.WriteLine(a == b);              // True  — compared by value
Console.WriteLine(ReferenceEquals(a, b)); // False — still two objects
Console.WriteLine(a);                   // Customer { Name = Asha, Email = asha@example.com, City = Bengaluru }

// a.Email = "new@example.com";         // ❌ init-only
var moved = a with { City = "Pune" };   // copy with one change
Console.WriteLine(moved.City);          // Pune
Console.WriteLine(a.City);              // Bengaluru — original untouched
""", "Records.cs")}
<h4>Records with extra members and validation</h4>
{C(r"""
public record Money(decimal Amount, string Currency)
{
    // Validate by re-declaring the property with an initializer
    public decimal Amount { get; init; } = Amount >= 0
        ? Amount
        : throw new ArgumentOutOfRangeException(nameof(Amount));

    public Money Add(Money other) =>
        other.Currency == Currency
            ? this with { Amount = Amount + other.Amount }
            : throw new InvalidOperationException("Currency mismatch");

    public override string ToString() => $"{Amount:N2} {Currency}";   // customise output
}

// Nominal record: properties instead of a parameter list
public record OrderLine
{
    public required string Sku { get; init; }
    public int Quantity { get; init; } = 1;
    public decimal UnitPrice { get; init; }
    public decimal Total => Quantity * UnitPrice;
}
""")}
<h4>Record inheritance</h4>
{C(r"""
public abstract record Payment(decimal Amount);
public record UpiPayment(decimal Amount, string Vpa) : Payment(Amount);
public record CardPayment(decimal Amount, string Last4) : Payment(Amount);

Payment p = new UpiPayment(499m, "asha@okbank");
Console.WriteLine(p);   // UpiPayment { Amount = 499, Vpa = asha@okbank }

// Equality also checks the runtime type:
Console.WriteLine(new UpiPayment(1, "x") == (Payment)new UpiPayment(1, "x"));   // True
""")}

<h3>3. record struct</h3>
{C(r"""
public readonly record struct DateRange(DateOnly Start, DateOnly End)
{
    public int Days => End.DayNumber - Start.DayNumber + 1;
    public bool Contains(DateOnly d) => d >= Start && d <= End;
    public bool Overlaps(DateRange other) => Start <= other.End && other.Start <= End;
}

var leave = new DateRange(new DateOnly(2026, 12, 22), new DateOnly(2026, 12, 31));
Console.WriteLine(leave.Days);                                  // 10
Console.WriteLine(leave.Contains(new DateOnly(2026, 12, 25)));  // True
""", "DateRange.cs")}

<h3>4. Tuples</h3>
<p><code>ValueTuple</code> groups values without declaring a type. Name the elements; <code>Item1</code>/<code>Item2</code> are hard to read.</p>
{C(r"""
// Return several values from a method
static (decimal Subtotal, decimal Gst, decimal Total) PriceCart(decimal[] prices)
{
    decimal subtotal = prices.Sum();
    decimal gst = Math.Round(subtotal * 0.18m, 2);
    return (subtotal, gst, subtotal + gst);
}

var bill = PriceCart([499m, 1299m, 89m]);
Console.WriteLine($"{bill.Subtotal} + {bill.Gst} = {bill.Total}");   // 1887 + 339.66 = 2226.66

// Tuple equality compares element by element (C# 7.3)
Console.WriteLine((1, "a") == (1, "a"));   // True

// Swap without a temp variable
int x = 1, y = 2;
(x, y) = (y, x);
Console.WriteLine($"{x} {y}");             // 2 1
""")}
{tip("Tuples are great inside one class or method. Once the same shape appears in several places or crosses a public API, promote it to a record.")}

<h3>5. Deconstruction</h3>
{C(r"""
// Tuples
var (sub, gst, total) = PriceCart([100m, 200m]);
var (_, _, onlyTotal) = PriceCart([100m]);           // discards

// Records (positional records generate Deconstruct)
var (name, email, city) = new Customer("Ravi", "ravi@example.com");

// Your own types: add a Deconstruct method
public class Employee
{
    public string FirstName { get; init; } = "";
    public string LastName { get; init; } = "";
    public decimal Salary { get; init; }

    public void Deconstruct(out string fullName, out decimal salary)
    {
        fullName = $"{FirstName} {LastName}";
        salary = Salary;
    }
}

var (full, pay) = new Employee { FirstName = "Meera", LastName = "Iyer", Salary = 90_000 };

// Deconstruct in foreach over a dictionary
var stock = new Dictionary<string, int> { ["SKU-1"] = 12, ["SKU-2"] = 0 };
foreach (var (sku, qty) in stock)
    Console.WriteLine($"{sku}: {qty}");
""")}

<h3>6. Which one should I use?</h3>
{table(["Type","Kind","Equality","Mutability","Best for"],[
["class","Reference","Reference (by default)","Mutable by default","Entities with identity and behaviour"],
["struct","Value","Field-by-field (slow, reflection) unless overridden","Prefer readonly","Tiny values, high-volume math"],
["record (class)","Reference","Value (generated)","Immutable by default","DTOs, API requests/responses, events, value objects"],
["record struct","Value","Value (generated)","Mutable unless readonly","Small value objects"],
["tuple","Value","Value","Mutable","Short-lived multi-value returns"]])}
''',
["Making large or mutable structs.",
"Forgetting that a struct always has a <code>default</code> value that skips your constructor's validation.",
"Using records for EF Core entities that get updated: their value equality confuses change tracking. Use classes for entities.",
"Returning unnamed tuples from public methods (<code>Item1</code>, <code>Item2</code>).",
"Expecting <code>with</code> to deep-copy: it copies references to nested objects (shallow)."],
("40 min", ["Create <code>record Address(string Line1, string City, string PinCode)</code> and <code>record Customer(string Name, Address Address)</code>. Show that two customers with equal addresses are equal.",
"Use <code>with</code> to move a customer to another city and print both versions.",
"Write <code>(int Min, int Max, double Average) Stats(int[] values)</code>, then deconstruct its result."]),
[("Are records reference types or value types?","<code>record</code> / <code>record class</code> is a reference type. <code>record struct</code> is a value type."),
("Does with deep-copy nested objects?","No. It's a shallow copy: reference-type properties point to the same nested objects."),
("Can a struct inherit from another struct?","No. Structs are implicitly sealed and can't have a base type other than ValueType, but they can implement interfaces.")],
[("Basic","What is the difference between a class and a struct?","A class is a reference type allocated on the heap, copied by reference, supports inheritance and can be null. A struct is a value type stored inline, copied by value, can't inherit, and always has a default value. Use structs for small immutable values and classes for everything else."),
("Basic","What is a record and when would you use one?","A record is a type whose equality is based on its data. The compiler generates Equals, GetHashCode, ==, ToString, Deconstruct and with-support. Use records for immutable data carriers: DTOs, API contracts, domain events and value objects."),
("Basic","What does the with expression do?","It creates a shallow copy of a record (or struct, or anonymous type) with the specified properties changed, leaving the original unchanged. Under the hood it calls a generated clone method then sets the init properties."),
("Intermediate","record vs record struct vs class — how do you choose?","Class for entities with identity and mutable state. Record class for immutable data with value equality, passed by reference (cheap to pass, allocates on the heap). Readonly record struct for very small value objects where you want value semantics and no heap allocation."),
("Intermediate","Why shouldn't you use records as EF Core entities?","Entities have identity (their key) and are mutated and tracked. Record value equality makes two entities with the same data look equal, conflicting with identity semantics and change tracking, and with-expressions produce new untracked instances."),
("Intermediate","What is the default value problem with structs?","Every struct has a default (all zero bits) created by <code>default</code>, array allocation or uninitialised fields. It bypasses your constructor, so validation can't guarantee invariants. Design structs so that zero is a valid state, or validate at use.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Pattern matching in depth",
"Replace nested if/else and casting with expressive patterns: type, property, relational, logical, positional and list patterns.",
[("Pattern","A test that a value has a certain shape, with optional variable capture."),
("Declaration pattern","<code>x is Circle c</code> — tests the type and assigns a typed variable."),
("Type pattern","<code>x is Circle</code> or a switch arm <code>Circle =&gt; …</code> — tests the type only."),
("Constant pattern","Compares against a constant: <code>is null</code>, <code>is 0</code>, <code>\"IN\" =&gt;</code>."),
("Relational pattern","<code>&lt;</code>, <code>&gt;</code>, <code>&lt;=</code>, <code>&gt;=</code> against a constant (C# 9)."),
("Logical pattern","Combine patterns with <code>and</code>, <code>or</code>, <code>not</code> (C# 9)."),
("Property pattern","<code>{ Status: \"Paid\", Total: &gt; 1000 }</code> — matches property values.".replace("{","{").replace("}","}")),
("Extended property pattern","<code>{ Address.City: \"Pune\" }</code> — nested member access (C# 10)."),
("Positional pattern","Matches using Deconstruct: <code>(\"IN\", &gt; 1)</code> or <code>Point(0, 0)</code>."),
("List pattern","Matches arrays/lists by element: <code>[1, .., 9]</code>, <code>[var first, ..]</code> (C# 11)."),
("Slice pattern","<code>..</code> inside a list pattern matches zero or more elements; <code>.. var rest</code> captures them."),
("Case guard (when)","An extra boolean condition on a switch arm."),
("Exhaustiveness","The compiler warns when a switch expression doesn't cover all inputs.")],
["Use <code>is null</code> / <code>is not null</code> for null checks; they can't be fooled by an overloaded ==.",
"Switch expressions + patterns turn business rules into readable tables.",
"Order arms from most specific to least specific; the compiler errors on unreachable arms.",
"End with <code>_ =&gt;</code> or throw, unless the compiler confirms you're exhaustive.",
"Property patterns read nested data without null checks: a null object simply doesn't match.",
"List patterns are great for parsing commands and arguments."],
f'''
<h3>1. Type and declaration patterns, and null checks</h3>
{C(r"""
object input = 42;

if (input is int n && n > 0)        // declaration pattern + condition
    Console.WriteLine($"Positive int {n}");

if (input is not string)             // negated type pattern
    Console.WriteLine("Not a string");

Customer? customer = FindCustomer(7);
if (customer is null) return;        // preferred over == null
if (customer is not null) { /* ... */ }

string Describe(object o) => o switch
{
    null            => "nothing",
    int i           => $"int {i}",
    decimal d       => $"money {d:C}",
    string { Length: 0 } => "empty string",
    string s        => $"text '{s}'",
    IEnumerable<int> nums => $"{nums.Count()} numbers",
    _               => o.GetType().Name
};
""")}

<h3>2. Property and extended property patterns</h3>
{C(r"""
public record Address(string City, string State, string PinCode);
public record Customer(string Name, Address Address, bool IsPrime);
public record Order(int Id, Customer Customer, decimal Total, string Status);

decimal DeliveryFee(Order o) => o switch
{
    { Customer.IsPrime: true }                          => 0m,     // extended property pattern
    { Total: >= 499 }                                   => 0m,
    { Customer.Address.State: "KA" or "TN" or "KL" }    => 40m,
    { Customer.Address.PinCode: ['1', '1', ..] }        => 60m,    // Delhi pins start with 11
    _                                                   => 80m
};

var o = new Order(1, new Customer("Asha", new Address("Mysuru", "KA", "570001"), false), 250m, "Placed");
Console.WriteLine(DeliveryFee(o));   // 40
""", "DeliveryFee.cs")}
{tip("If <code>o.Customer</code> were null, <code>{ Customer.IsPrime: true }</code> simply wouldn't match. No NullReferenceException.".replace("{","{").replace("}","}"))}

<h3>3. Relational and logical patterns</h3>
{C(r"""
string TaxSlab(decimal income) => income switch
{
    <= 400_000                  => "Nil",
    > 400_000 and <= 800_000    => "5%",
    > 800_000 and <= 1_200_000  => "10%",
    > 1_200_000 and <= 1_600_000 => "15%",
    > 1_600_000 and <= 2_000_000 => "20%",
    > 2_000_000 and <= 2_400_000 => "25%",
    _                           => "30%"
};   // illustrative slabs — check the current rules before using for real tax

bool IsWeekend(DayOfWeek d) => d is DayOfWeek.Saturday or DayOfWeek.Sunday;
bool IsLetter(char c) => c is (>= 'a' and <= 'z') or (>= 'A' and <= 'Z');
bool IsValidPercent(int p) => p is >= 0 and <= 100;
""")}

<h3>4. Positional patterns and tuple switches</h3>
<p>Switching on a tuple turns a state machine into a readable table.</p>
{C(r"""
public enum OrderState { Placed, Paid, Shipped, Delivered, Cancelled }
public enum OrderAction { Pay, Ship, Deliver, Cancel }

OrderState Next(OrderState state, OrderAction action) => (state, action) switch
{
    (OrderState.Placed,  OrderAction.Pay)     => OrderState.Paid,
    (OrderState.Paid,    OrderAction.Ship)    => OrderState.Shipped,
    (OrderState.Shipped, OrderAction.Deliver) => OrderState.Delivered,
    (OrderState.Placed or OrderState.Paid, OrderAction.Cancel) => OrderState.Cancelled,
    _ => throw new InvalidOperationException($"Can't {action} an order that is {state}")
};

Console.WriteLine(Next(OrderState.Placed, OrderAction.Pay));      // Paid
// Next(OrderState.Shipped, OrderAction.Cancel);                  // throws

// Positional pattern with a record's Deconstruct
public record Point(int X, int Y);
string Quadrant(Point p) => p switch
{
    (0, 0)              => "origin",
    (> 0, > 0)          => "Q1",
    (< 0, > 0)          => "Q2",
    (< 0, < 0)          => "Q3",
    (> 0, < 0)          => "Q4",
    _                   => "on an axis"
};
""", "OrderStateMachine.cs")}

<h3>5. List patterns (C# 11)</h3>
{C(r"""
int[] nums = [1, 2, 3, 4, 5];

Console.WriteLine(nums is [1, 2, 3, 4, 5]);     // True — exact
Console.WriteLine(nums is [1, ..]);             // True — starts with 1
Console.WriteLine(nums is [.., 5]);             // True — ends with 5
Console.WriteLine(nums is [_, _, ..]);          // True — at least 2 elements
if (nums is [var first, .. var middle, var last])
    Console.WriteLine($"{first} | {string.Join(",", middle)} | {last}");   // 1 | 2,3,4 | 5

// Parse console commands
string Run(string[] args) => args switch
{
    []                                  => "Usage: lib <command>",
    ["list"]                            => "Listing all items",
    ["borrow", var member, var item]    => $"Member {member} borrows {item}",
    ["return", var item]                => $"Returning {item}",
    ["search", .. var words] when words.Length > 0 => $"Searching '{string.Join(' ', words)}'",
    [var cmd, ..]                       => $"Unknown command '{cmd}'"
};

Console.WriteLine(Run("borrow 1001 5".Split(' ')));      // Member 1001 borrows 5
Console.WriteLine(Run("search clean code".Split(' ')));  // Searching 'clean code'
""")}

<h3>6. Guards and a small rules engine</h3>
{C(r"""
public record LoanApplication(int Age, decimal MonthlyIncome, int CreditScore, decimal ExistingEmi);

string Decide(LoanApplication a) => a switch
{
    { Age: < 21 or > 60 }                         => "Rejected: age",
    { CreditScore: < 650 }                        => "Rejected: credit score",
    { MonthlyIncome: < 25_000 }                   => "Rejected: income",
    var x when x.ExistingEmi > x.MonthlyIncome * 0.5m => "Rejected: EMI burden above 50%",
    { CreditScore: >= 780, MonthlyIncome: >= 100_000 } => "Approved: premium rate",
    _                                             => "Approved: standard rate"
};

Console.WriteLine(Decide(new(30, 120_000, 800, 10_000)));  // Approved: premium rate
Console.WriteLine(Decide(new(30, 60_000, 720, 35_000)));   // Rejected: EMI burden above 50%
""", "LoanRules.cs")}
''',
["Writing an arm that's already covered by an earlier one (CS8510 unreachable).",
"Forgetting the <code>_</code> arm; a missing case throws <code>SwitchExpressionException</code> at runtime.",
"Using <code>== null</code> on types that overload <code>==</code>; prefer <code>is null</code>.",
"Over-nesting patterns until nobody can read them; extract a well-named method.",
"Using patterns to select behaviour that belongs in a virtual method (Week 2, Day 4)."],
("40 min", ["Write <code>ShippingZone(string pinCode)</code> using list patterns on the first digit (pin zones 1–9).",
"Model a traffic light as <code>(Light, int SecondsElapsed)</code> and write <code>Next</code> with a tuple switch.",
"Build a mini command parser for <code>add &lt;name&gt; &lt;email&gt;</code>, <code>list</code>, <code>delete &lt;id&gt;</code> using list patterns."]),
[("What's the difference between is and a switch expression?","<code>is</code> tests one pattern and returns bool. A switch expression tests several patterns in order and returns the value of the first matching arm."),
("What happens if no switch-expression arm matches?","A <code>SwitchExpressionException</code> is thrown at runtime. The compiler warns (CS8509) when it can tell the switch isn't exhaustive."),
("Do property patterns handle null?","Yes. A property pattern requires a non-null value, so null simply fails to match.")],
[("Basic","What is pattern matching in C#?","A set of language features (is, switch statements/expressions) that test a value against a shape — type, constant, range, property values, position or list elements — and optionally extract parts of it into variables, replacing manual casts and nested ifs."),
("Basic","Why prefer 'is null' over '== null'?","<code>==</code> can be overloaded by a type and may behave unexpectedly; <code>is null</code> always performs a true null check. It also reads consistently with <code>is not null</code>."),
("Basic","What are relational and logical patterns?","Relational patterns compare with <, >, <=, >= against constants; logical patterns combine patterns with and, or and not. Example: <code>score is >= 0 and <= 100</code>."),
("Intermediate","What are list patterns and give a use case.","C# 11 patterns that match sequences by elements and length, with <code>..</code> for slices. Use cases: parsing command-line arguments, validating fixed-format codes, checking prefixes/suffixes of arrays."),
("Intermediate","How would you implement a state machine with pattern matching?","Switch on a tuple of (currentState, trigger), with one arm per valid transition returning the next state and a final arm that throws for invalid transitions. It's compact, readable and easy to review against a state diagram."),
("Intermediate","When is a switch expression not exhaustive even with enums?","Enums can hold any value of their underlying type, not just named members, so the compiler still requires a discard arm (or warns) even if every named value is listed.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Enums, object, Equals/GetHashCode and boxing",
"Use enums and flags correctly, implement equality that works with dictionaries and sets, and spot hidden boxing.",
[("enum","A value type defining a set of named integral constants, e.g. <code>OrderStatus.Paid</code>."),
("Underlying type","The integral type behind an enum, <code>int</code> by default; can be byte, short, long etc."),
("[Flags]","An attribute marking an enum whose values are bit flags that can be combined with |."),
("Bitwise operators","<code>|</code> combine, <code>&amp;</code> test, <code>~</code> invert, <code>^</code> toggle bits."),
("Reference equality","Two references point to the same object (<code>ReferenceEquals</code>)."),
("Value equality","Two objects hold equal data."),
("IEquatable&lt;T&gt;","Interface providing a strongly typed <code>Equals(T other)</code>, avoiding boxing for structs."),
("Hash code","An int derived from an object's data, used by Dictionary and HashSet to pick a bucket."),
("HashCode.Combine","Helper that produces a good hash code from several fields."),
("Boxing","Copying a value type into a new heap object so it can be treated as object or an interface."),
("Unboxing","Copying the value back out of the box; requires a cast to the exact type."),
("System.Object","Root of all types; defines Equals, GetHashCode, ToString, GetType, MemberwiseClone.")],
["Store enums by name in JSON/APIs where possible; numbers break when members are reordered.",
"Give [Flags] members powers of two and include <code>None = 0</code>.",
"Override Equals and GetHashCode together, always.",
"Equal objects must have equal hash codes; unequal objects may share one.",
"Never use mutable fields in GetHashCode for objects stored in a dictionary or set.",
"Boxing hides in non-generic APIs, interface calls on structs and <code>object</code> parameters."],
f'''
<h3>1. Enums</h3>
{C(r"""
public enum OrderStatus
{
    Placed = 1,          // explicit values: safe to store in a database
    Paid = 2,
    Shipped = 3,
    Delivered = 4,
    Cancelled = 9
}

var s = OrderStatus.Paid;
Console.WriteLine(s);                 // Paid
Console.WriteLine((int)s);            // 2
Console.WriteLine(s.ToString().ToLowerInvariant());

// Parse safely from user input or an API
if (Enum.TryParse<OrderStatus>("shipped", ignoreCase: true, out var parsed))
    Console.WriteLine(parsed);        // Shipped

// Casting any int "works" — validate external numbers
var weird = (OrderStatus)42;
Console.WriteLine(Enum.IsDefined(weird));   // False

// Iterate all values
foreach (OrderStatus st in Enum.GetValues<OrderStatus>())
    Console.Write($"{st} ");          // Placed Paid Shipped Delivered Cancelled

// Exhaustive switch still needs a discard
string Icon(OrderStatus st) => st switch
{
    OrderStatus.Placed    => "🕒",
    OrderStatus.Paid      => "💳",
    OrderStatus.Shipped   => "🚚",
    OrderStatus.Delivered => "✅",
    OrderStatus.Cancelled => "✖",
    _ => throw new ArgumentOutOfRangeException(nameof(st))
};
""", "OrderStatus.cs")}

<h3>2. Flags enums</h3>
{C(r"""
[Flags]
public enum Permission
{
    None    = 0,
    Read    = 1 << 0,   // 1
    Write   = 1 << 1,   // 2
    Delete  = 1 << 2,   // 4
    Approve = 1 << 3,   // 8
    Editor  = Read | Write,
    Admin   = Read | Write | Delete | Approve
}

Permission p = Permission.Read | Permission.Write;
Console.WriteLine(p);                              // Editor   (named combination)
Console.WriteLine(p.HasFlag(Permission.Write));    // True
Console.WriteLine((p & Permission.Delete) != 0);   // False

p |= Permission.Approve;    // grant
p &= ~Permission.Write;     // revoke
Console.WriteLine(p);       // Read, Approve
""", "Permission.cs")}

<h3>3. Equality in .NET</h3>
{table(["","Class (default)","Struct (default)","Record","string"],[
["<code>==</code>","Reference","Not defined (compile error)","Value","Value"],
["<code>Equals</code>","Reference","Field-by-field via reflection (slow)","Value","Value"],
["<code>ReferenceEquals</code>","Reference","Always false (boxes)","Reference","Reference"]])}
{C(r"""
var p1 = new Product("SKU-1", "Pen");
var p2 = new Product("SKU-1", "Pen");
Console.WriteLine(p1 == p2);          // False — different objects (class without overrides)

var set = new HashSet<Product> { p1, p2 };
Console.WriteLine(set.Count);         // 2 — HashSet thinks they're different

public class Product(string sku, string name)
{
    public string Sku { get; } = sku;
    public string Name { get; } = name;
}
""")}

<h3>4. Implementing equality properly</h3>
<p>Decide what makes two objects "the same". For a product it's the SKU, not the name.</p>
{C(r"""
public sealed class Product : IEquatable<Product>
{
    public string Sku { get; }
    public string Name { get; set; }      // mutable, so NOT part of equality

    public Product(string sku, string name)
    {
        Sku = sku.Trim().ToUpperInvariant();
        Name = name;
    }

    public bool Equals(Product? other) =>
        other is not null && Sku == other.Sku;

    public override bool Equals(object? obj) => Equals(obj as Product);

    public override int GetHashCode() => Sku.GetHashCode();

    public static bool operator ==(Product? a, Product? b) => a is null ? b is null : a.Equals(b);
    public static bool operator !=(Product? a, Product? b) => !(a == b);
}

var set = new HashSet<Product> { new("sku-1", "Pen"), new("SKU-1", "Blue pen") };
Console.WriteLine(set.Count);    // 1 ✓
""", "Product.cs")}
{C(r"""
// Several fields? Use HashCode.Combine
public override int GetHashCode() => HashCode.Combine(CountryCode, PhoneNumber);
""")}
<h4>The equality contract</h4>
<ul>
<li><b>Reflexive:</b> <code>x.Equals(x)</code> is true.</li>
<li><b>Symmetric:</b> <code>x.Equals(y)</code> equals <code>y.Equals(x)</code>.</li>
<li><b>Transitive:</b> if x = y and y = z, then x = z.</li>
<li><b>Consistent with GetHashCode:</b> equal objects return equal hash codes.</li>
<li><code>x.Equals(null)</code> is false and never throws.</li>
</ul>
{warn("If an object's hash code changes while it's inside a Dictionary key or HashSet, you can no longer find or remove it. Base hash codes on immutable fields.", "Danger")}
{tip("Records do all of this for you, including IEquatable&lt;T&gt;, == and !=. Hand-write equality only when the identity rule differs from 'all fields'.")}

<h3>5. Boxing in practice</h3>
{C(r"""
long before = GC.GetAllocatedBytesForCurrentThread();

object total = 0;
for (int i = 0; i < 1_000_000; i++)
    total = (int)total + i;          // unbox + box every iteration

long after = GC.GetAllocatedBytesForCurrentThread();
Console.WriteLine($"{(after - before) / 1024 / 1024} MB allocated");   // ≈ 22 MB

before = GC.GetAllocatedBytesForCurrentThread();
int sum = 0;
for (int i = 0; i < 1_000_000; i++) sum += i;
Console.WriteLine($"{GC.GetAllocatedBytesForCurrentThread() - before} bytes");  // 0
""", "BoxingDemo.cs")}
{table(["Hidden boxing","Fix"],[
["<code>ArrayList</code>, <code>Hashtable</code>","<code>List&lt;T&gt;</code>, <code>Dictionary&lt;K,V&gt;</code>"],
["Struct passed as an interface (<code>IComparable c = myStruct</code>)","Generic constraint <code>where T : IComparable&lt;T&gt;</code>"],
["<code>object</code> parameters (<code>void Log(object o)</code>)","Generic method <code>Log&lt;T&gt;(T value)</code>"],
["Struct without Equals override in a Dictionary key","Implement <code>IEquatable&lt;T&gt;</code> or use a record struct"]])}
''',
["Relying on enum numeric values in JSON or a DB without fixing them explicitly.",
"Flags enums without powers of two, so combinations collide.",
"Overriding Equals but not GetHashCode (CS0659 warning) — dictionaries break.",
"Including mutable properties in GetHashCode.",
"Using <code>==</code> on two <code>object</code> variables holding boxed ints: <code>(object)1 == (object)1</code> is false."],
("40 min", ["Create a <code>[Flags] enum WorkDays</code> and a method that prints which days an employee works and whether they work weekends.",
"Write a <code>PhoneNumber</code> class (country code + number) with full equality, then prove it works in a HashSet and as a Dictionary key.",
"Measure boxing with <code>GC.GetAllocatedBytesForCurrentThread</code> using an <code>ArrayList</code> vs <code>List&lt;int&gt;</code> of 100,000 ints."]),
[("Why must Equals and GetHashCode be overridden together?","Hash-based collections first compare hash codes to find a bucket, then call Equals. If equal objects have different hash codes, the collection looks in the wrong bucket and never finds a match."),
("Is (object)5 == (object)5 true?","No. Each cast boxes into a separate object and <code>==</code> on object compares references. <code>Equals</code> would return true."),
("What should a [Flags] enum's zero value be named?","<code>None</code>, meaning no flags set. Don't give a real flag the value 0, because HasFlag(0) is always true.")],
[("Basic","What is an enum and what is its default underlying type?","A value type that defines a set of named integral constants. The default underlying type is int, and the first member is 0 unless you assign values."),
("Basic","What is the difference between == and Equals()?","For reference types without overloads, == compares references; Equals can be overridden for value comparison. string and records overload both to compare values. For value types, Equals compares values and == only exists if the type defines it."),
("Basic","What is boxing and unboxing?","Boxing converts a value type to object (or an interface) by copying it into a new heap object. Unboxing extracts it with an explicit cast to the exact type. Both cost CPU and boxing creates garbage."),
("Intermediate","What are the rules for implementing GetHashCode?","Equal objects must return equal hash codes; the value should not change while the object is in a hash-based collection; it should be fast and well distributed. Use HashCode.Combine over the same fields used in Equals."),
("Intermediate","What happens if you mutate a key after adding it to a Dictionary?","If the mutation changes its hash code, the dictionary keeps it in the old bucket. Lookups, ContainsKey and Remove fail to find it, effectively leaking the entry."),
("Intermediate","What is a [Flags] enum and how do you test a flag?","An enum whose members are distinct bits combined with |. Test with <code>(value & Flag) == Flag</code> or <code>value.HasFlag(Flag)</code> (no longer boxes in modern .NET). Remove with <code>value &= ~Flag</code>.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Exceptions: try/catch/finally, custom exceptions, throw vs throw ex",
"Handle errors at the right level, preserve stack traces, write meaningful custom exceptions, and know when not to use exceptions at all.",
[("Exception","An object describing an error that interrupts normal flow and propagates up the call stack until caught."),
("Throw","Raising an exception: <code>throw new InvalidOperationException(\"…\")</code>."),
("try / catch / finally","try runs code; catch handles matching exceptions; finally always runs for cleanup."),
("Exception filter","<code>catch (HttpRequestException ex) when (ex.StatusCode == 404)</code> — catches only when the condition is true, without unwinding the stack first."),
("Stack trace","The list of method calls active when the exception was thrown; vital for debugging."),
("Rethrow (throw;)","Re-raises the current exception preserving its original stack trace."),
("throw ex","Re-raises the exception but resets the stack trace to the current line. Avoid."),
("Inner exception","The original exception wrapped inside a new, higher-level one (<code>new XException(\"…\", ex)</code>)."),
("Custom exception","Your own class deriving from Exception that names a domain-specific failure."),
("Unhandled exception","One that reaches the top of the stack uncaught; the process terminates (console) or the request returns 500 (ASP.NET Core)."),
("Guard clause helpers","<code>ArgumentNullException.ThrowIfNull</code>, <code>ArgumentOutOfRangeException.ThrowIfNegative</code> (.NET 8) etc."),
("Fail fast","Detect invalid input early and throw immediately rather than continuing in a bad state.")],
["Throw for things that shouldn't happen; return a result for expected outcomes.",
"Catch only what you can handle, at the level where you can do something useful.",
"Use <code>throw;</code> to rethrow, never <code>throw ex;</code>.",
"Wrap low-level exceptions in domain ones and pass the original as the inner exception.",
"finally (or <code>using</code>) for cleanup that must always run.",
"Catch <code>Exception</code> only at the top level (Program, middleware) to log and fail gracefully."],
f'''
<h3>1. The exception hierarchy</h3>
{table(["Exception","Thrown when","Typical fix"],[
["<code>ArgumentNullException</code>","A required argument is null","Guard clause at method start"],
["<code>ArgumentOutOfRangeException</code>","Value outside the allowed range","Validate input"],
["<code>ArgumentException</code>","Argument is invalid for another reason","Validate input"],
["<code>InvalidOperationException</code>","Call isn't valid for the object's current state","Check state first"],
["<code>NullReferenceException</code>","Dereferencing null","Fix the bug; enable nullable warnings"],
["<code>KeyNotFoundException</code>","Dictionary indexer with missing key","Use TryGetValue"],
["<code>FormatException</code>","Parse of badly formatted text","Use TryParse"],
["<code>IOException</code> / <code>FileNotFoundException</code>","File/stream problems","Catch and report to the user"],
["<code>HttpRequestException</code>","Network/HTTP failure","Retry or report (Week 43)"],
["<code>OperationCanceledException</code>","A cancellation token fired","Usually let it propagate"],
["<code>NotImplementedException</code>","Placeholder code","Never ship it"]])}
<p>All derive from <code>System.Exception</code>, which carries <code>Message</code>, <code>StackTrace</code>, <code>InnerException</code> and <code>Data</code>.</p>

<h3>2. try / catch / finally</h3>
{C(r"""
static decimal ReadPriceFromFile(string path)
{
    StreamReader? reader = null;
    try
    {
        reader = new StreamReader(path);
        string line = reader.ReadLine() ?? throw new InvalidDataException("File is empty");
        return decimal.Parse(line);
    }
    catch (FileNotFoundException ex)                 // most specific first
    {
        Console.WriteLine($"Missing file: {ex.FileName}");
        return 0m;
    }
    catch (FormatException)
    {
        Console.WriteLine("Price isn't a number");
        return 0m;
    }
    catch (IOException ex) when (ex.HResult == unchecked((int)0x80070020))   // filter: file locked
    {
        Console.WriteLine("File is in use; try again");
        return 0m;
    }
    finally
    {
        reader?.Dispose();                           // ALWAYS runs: success, catch, or uncaught
        Console.WriteLine("Cleaned up");
    }
}
""")}
<p>The <code>using</code> statement is shorthand for try/finally + Dispose:</p>
{C(r"""
static decimal ReadPrice(string path)
{
    using var reader = new StreamReader(path);       // disposed at end of method
    return decimal.Parse(reader.ReadLine() ?? "0");
}
""")}
{warn("Order catch blocks from most specific to most general. <code>catch (Exception)</code> first would make the others unreachable (compile error CS0160).", "Rule")}

<h3>3. throw vs throw ex vs wrapping</h3>
{C(r"""
void Level3() => throw new InvalidOperationException("Disk quota exceeded");
void Level2() => Level3();

void RethrowCorrectly()
{
    try { Level2(); }
    catch (InvalidOperationException ex)
    {
        Log(ex);
        throw;                     // ✓ stack trace still points to Level3
    }
}

void RethrowBadly()
{
    try { Level2(); }
    catch (InvalidOperationException ex)
    {
        throw ex;                  // ✗ stack trace now starts HERE; Level3 is lost (CA2200)
    }
}

void WrapWithContext(int orderId)
{
    try { Level2(); }
    catch (InvalidOperationException ex)
    {
        // ✓ add context, keep the original as InnerException
        throw new OrderProcessingException($"Order {orderId} could not be saved", ex);
    }
}
""")}

<h3>4. Custom exceptions</h3>
<p>Create one when callers need to catch a specific business failure, or when it carries useful data.</p>
{C(r"""
public class InsufficientFundsException : Exception
{
    public string AccountNumber { get; }
    public decimal Requested { get; }
    public decimal Available { get; }

    public InsufficientFundsException(string accountNumber, decimal requested, decimal available)
        : base($"Account {accountNumber}: requested {requested:N2}, available {available:N2}")
    {
        AccountNumber = accountNumber;
        Requested = requested;
        Available = available;
    }

    public InsufficientFundsException(string message, Exception inner) : base(message, inner) { }

    public decimal Shortfall => Requested - Available;
}

public class OrderProcessingException(string message, Exception? inner = null)
    : Exception(message, inner);
""", "Exceptions.cs")}
{C(r"""
try
{
    account.Withdraw(25_000m);
}
catch (InsufficientFundsException ex)
{
    Console.WriteLine($"Short by {ex.Shortfall:N2}. {ex.Message}");
}
""")}
<ul>
<li>Name ends with <code>Exception</code>; derive from <code>Exception</code> (not ApplicationException).</li>
<li>Provide a meaningful message and useful properties.</li>
<li>Offer a constructor taking an inner exception.</li>
</ul>

<h3>5. Guard clauses with the built-in helpers</h3>
{C(r"""
public void Transfer(Account? to, decimal amount, string? reference)
{
    ArgumentNullException.ThrowIfNull(to);                    // .NET 6
    ArgumentOutOfRangeException.ThrowIfNegativeOrZero(amount); // .NET 8
    ArgumentOutOfRangeException.ThrowIfGreaterThan(amount, 1_000_000m);
    ArgumentException.ThrowIfNullOrWhiteSpace(reference);      // .NET 7
    // parameter names are captured automatically via CallerArgumentExpression
    // ...
}
""")}

<h3>6. Best practices</h3>
{table(["Do","Don't"],[
["Throw when a method can't do what its name promises","Use exceptions for normal control flow (e.g. 'user not found' in a search)"],
["Catch specific types you can recover from","<code>catch (Exception) { }</code> — swallowing hides bugs"],
["Log once, at the boundary","Log and rethrow at every layer (duplicate logs)"],
["Use TryParse / TryGetValue for expected failures","Wrap Parse in try/catch in a loop"],
["Add context by wrapping with an inner exception","Lose the original exception"],
["Have one top-level handler","Let a console app crash with a raw stack trace for users"]])}
{C(r"""
// Top-level safety net in Program.cs
AppDomain.CurrentDomain.UnhandledException += (_, e) =>
    Console.Error.WriteLine($"Fatal: {(e.ExceptionObject as Exception)?.Message}");

try
{
    RunApp();
}
catch (Exception ex)
{
    Console.Error.WriteLine($"Something went wrong: {ex.Message}");
    Environment.ExitCode = 1;
}
""", "Program.cs")}
''',
["<code>throw ex;</code> — destroys the stack trace.",
"Empty catch blocks.",
"Catching <code>NullReferenceException</code> instead of fixing the null.",
"Throwing <code>Exception</code> itself — callers can't catch it selectively.",
"Using exceptions for validation failures you expect thousands of times per second."],
("40 min", ["Write a method that reads a CSV of prices. Handle missing file, empty file and bad numbers separately, and always print \"Done\" in finally.",
"Create <code>InvalidPinCodeException</code> with a <code>PinCode</code> property, and throw it from a validator.",
"Demonstrate <code>throw;</code> vs <code>throw ex;</code> by printing <code>ex.StackTrace</code> in both cases."]),
[("Does finally run if the catch block throws?","Yes. finally runs whether the try completes, a catch handles it, or an exception escapes. It doesn't run only if the process is killed (e.g. Environment.FailFast or a stack overflow)."),
("What is an exception filter's advantage over an if inside catch?","The filter runs before the stack unwinds, so when it's false the exception continues untouched (better diagnostics), and you avoid catch-and-rethrow."),
("Should you catch Exception?","Only at application boundaries (Program, middleware, background job runner) to log and fail gracefully. Elsewhere, catch specific types.")],
[("Basic","What is the difference between throw and throw ex?","<code>throw;</code> rethrows the current exception preserving the original stack trace. <code>throw ex;</code> rethrows the same object but resets the stack trace to the current location, losing where the error actually happened."),
("Basic","What is the purpose of the finally block?","To run cleanup code (closing files, releasing locks, disposing connections) regardless of whether an exception occurred or was caught. using statements compile to try/finally."),
("Basic","Can you have multiple catch blocks? In what order?","Yes, ordered from most derived to most general. The first matching block runs. Placing a base type first makes later blocks unreachable and is a compile error."),
("Intermediate","When should you create a custom exception?","When callers need to distinguish and handle a specific domain failure (InsufficientFundsException), or when the exception should carry structured data. Otherwise prefer built-in types like ArgumentException or InvalidOperationException."),
("Intermediate","Exceptions vs result objects — how do you decide?","Exceptions for unexpected failures or violations of a method's contract; result objects (or Try-patterns) for expected, frequent outcomes such as validation errors or 'not found'. Exceptions are expensive and hide control flow."),
("Intermediate","What are exception filters and why are they useful?","<code>catch (X ex) when (condition)</code>. The condition is evaluated before unwinding; if false, the exception keeps propagating as if never caught. They're useful for catching by error code, logging without catching (<code>when (Log(ex))</code> returning false), and keeping crash dumps accurate.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Delegates and events",
"Pass methods around as values with delegates, and build a publisher/subscriber design with events.",
[("Delegate","A type-safe reference to a method with a specific signature; can be stored, passed and invoked."),
("Delegate type","Declares the signature, e.g. <code>delegate decimal PriceRule(decimal price);</code>"),
("Multicast delegate","A delegate holding several methods; invoking it calls each in order."),
("Func&lt;…, TResult&gt;","Built-in generic delegate for methods that return a value."),
("Action&lt;…&gt;","Built-in generic delegate for methods that return void."),
("Lambda expression","Inline anonymous method: <code>x =&gt; x * 2</code>."),
("Event","A delegate-backed member that outside code can only subscribe (+=) to or unsubscribe (-=) from; only the owner can raise it."),
("Publisher","The class that declares and raises the event."),
("Subscriber","Code that attaches a handler to the event."),
("EventHandler&lt;TEventArgs&gt;","Standard delegate <code>void (object? sender, TEventArgs e)</code> for events."),
("EventArgs","Base class for event data; derive to carry details."),
("OnXxx method","Conventional <code>protected virtual</code> method that raises the event, so subclasses can hook in.")],
["A delegate is a variable that holds a method.",
"Use built-in Func/Action instead of declaring custom delegate types in most code.",
"Events let objects announce \"something happened\" without knowing who listens.",
"Raise with <code>Handler?.Invoke(this, args)</code> so no subscribers is safe.",
"Unsubscribe long-lived publishers' events, or the subscriber can't be garbage-collected.",
"The <code>event</code> keyword stops outsiders from raising or replacing the subscriber list."],
f'''
<h3>1. Delegates</h3>
{C(r"""
// 1. Declare a delegate type: any method taking decimal and returning decimal fits
public delegate decimal PriceRule(decimal price);

static decimal FestiveSale(decimal p) => p * 0.80m;
static decimal AddGst(decimal p) => p * 1.18m;

PriceRule rule = FestiveSale;        // 2. assign a method (no parentheses)
Console.WriteLine(rule(1000m));      // 3. invoke → 800.00

rule = AddGst;                       // swap behaviour at runtime
Console.WriteLine(rule(1000m));      // 1180.00

// Pass behaviour INTO a method
static decimal[] ApplyToAll(decimal[] prices, PriceRule r)
{
    var result = new decimal[prices.Length];
    for (int i = 0; i < prices.Length; i++) result[i] = r(prices[i]);
    return result;
}

var sale = ApplyToAll([100m, 250m], FestiveSale);   // [80, 200]
var inline = ApplyToAll([100m, 250m], p => p - 10);  // lambda: [90, 240]
""", "Delegates.cs")}

<h3>2. Func and Action</h3>
{C(r"""
Func<decimal, decimal> gst = p => p * 1.18m;            // takes decimal, returns decimal
Func<int, int, int> add = (a, b) => a + b;              // last type parameter = return type
Func<DateTime> now = () => DateTime.Now;                // no parameters
Action<string> log = msg => Console.WriteLine($"[LOG] {msg}");   // returns void
Predicate<int> isEven = n => n % 2 == 0;                // same as Func<int, bool>

log($"GST on 500 is {gst(500)}");
""")}
<p>You'll go deep on lambdas, closures and LINQ in Week 5. For now: Func returns a value, Action doesn't.</p>

<h3>3. Multicast delegates</h3>
{C(r"""
Action<string> notify = msg => Console.WriteLine($"Email: {msg}");
notify += msg => Console.WriteLine($"SMS:   {msg}");
notify += msg => Console.WriteLine($"Push:  {msg}");

notify("Order shipped");
// Email: Order shipped
// SMS:   Order shipped
// Push:  Order shipped

notify -= ...;   // remove a handler (needs a reference to the same method/lambda instance)
""")}
{warn("For a multicast <code>Func</code>, only the <b>last</b> method's return value is returned. Use multicast with void delegates.", "Gotcha")}

<h3>4. Events: publisher and subscribers</h3>
<p>An order doesn't need to know about emails, inventory or analytics. It just announces that its status changed.</p>
{C(r"""
public class OrderStatusChangedEventArgs(int orderId, string oldStatus, string newStatus) : EventArgs
{
    public int OrderId { get; } = orderId;
    public string OldStatus { get; } = oldStatus;
    public string NewStatus { get; } = newStatus;
    public DateTime ChangedAt { get; } = DateTime.UtcNow;
}

public class Order(int id)
{
    public int Id { get; } = id;
    public string Status { get; private set; } = "Placed";

    // 1. Declare the event
    public event EventHandler<OrderStatusChangedEventArgs>? StatusChanged;

    public void ChangeStatus(string newStatus)
    {
        if (newStatus == Status) return;
        string old = Status;
        Status = newStatus;
        OnStatusChanged(new OrderStatusChangedEventArgs(Id, old, newStatus));   // 2. raise
    }

    // 3. Conventional protected virtual raiser
    protected virtual void OnStatusChanged(OrderStatusChangedEventArgs e) =>
        StatusChanged?.Invoke(this, e);       // ?. = safe when nobody subscribed
}
""", "Order.cs")}
{C(r"""
var order = new Order(1042);

// Subscribers know about the order; the order knows nothing about them
order.StatusChanged += (sender, e) =>
    Console.WriteLine($"📧 Email: order {e.OrderId} is now {e.NewStatus}");

order.StatusChanged += OnInventoryUpdate;

order.ChangeStatus("Paid");
order.ChangeStatus("Shipped");

order.StatusChanged -= OnInventoryUpdate;     // unsubscribe a named method
order.ChangeStatus("Delivered");               // only the email handler runs now

static void OnInventoryUpdate(object? sender, OrderStatusChangedEventArgs e)
{
    if (e.NewStatus == "Shipped") Console.WriteLine($"📦 Inventory: release stock for {e.OrderId}");
}

// order.StatusChanged = null;          // ❌ can't assign from outside — that's what `event` protects
// order.StatusChanged?.Invoke(...);    // ❌ can't raise from outside
""", "Program.cs")}

<h3>5. Why the event keyword matters</h3>
{table(["","public delegate field","public event"],[
["Outsiders subscribe (+=)","Yes","Yes"],
["Outsiders replace all subscribers (=)","Yes ✗","No ✓"],
["Outsiders raise it","Yes ✗","No ✓"],
["Shows as an event in tooling","No","Yes"]])}

<h3>6. Pitfalls</h3>
<ul>
<li><b>Memory leaks:</b> the publisher holds references to subscribers. If a long-lived publisher (a static service) has a short-lived subscriber (a form, a view model), the subscriber never gets collected unless it unsubscribes.</li>
<li><b>Exceptions in handlers:</b> if one handler throws, later handlers don't run and the exception reaches the code that raised the event.</li>
<li><b>Synchronous:</b> handlers run on the raiser's thread, one after another. A slow handler slows the publisher.</li>
<li>Can't unsubscribe an anonymous lambda unless you stored it in a variable first.</li>
</ul>
{tip("In ASP.NET Core you'll mostly use other patterns for this (MediatR notifications, domain events, message queues), but they all build on the same publisher/subscriber idea.")}
''',
["Raising events without the null-conditional <code>?.</code> → NullReferenceException when nobody subscribed.",
"Using a public delegate field instead of an event.",
"Forgetting to unsubscribe from long-lived publishers.",
"Doing slow work (I/O, network) directly inside an event handler.",
"Expecting multicast Func to return all results."],
("40 min", ["Create <code>TemperatureSensor</code> with a <code>ThresholdExceeded</code> event (args: reading, threshold). Simulate 20 random readings.",
"Subscribe two handlers: one prints a warning, one counts alerts. Unsubscribe the counter after 3 alerts.",
"Write <code>ApplyDiscounts(decimal price, params Func&lt;decimal, decimal&gt;[] rules)</code> and chain three rules."]),
[("What's the difference between a delegate and an event?","An event is a delegate wrapped with access control: outside code can only add or remove handlers; only the declaring class can invoke or reset it."),
("Why use EventHandler&lt;T&gt; instead of a custom delegate?","It's the .NET convention (sender + args), works with tooling and avoids declaring a new delegate type for each event."),
("What does sender usually contain?","The object that raised the event (<code>this</code>), so handlers attached to many publishers know which one fired.")],
[("Basic","What is a delegate in C#?","A type-safe object that references one or more methods with a matching signature. It lets you pass methods as parameters, store them and invoke them later — the foundation of callbacks, events, LINQ and lambdas."),
("Basic","What is the difference between Func, Action and Predicate?","Func returns a value (last type parameter is the return type), Action returns void, and Predicate&lt;T&gt; returns bool (equivalent to Func&lt;T, bool&gt;)."),
("Basic","What is an event and how is it different from a delegate field?","An event is a member backed by a delegate, but outside code can only subscribe/unsubscribe. A public delegate field could be invoked or overwritten by anyone, breaking encapsulation."),
("Intermediate","How can events cause memory leaks?","The publisher's delegate list holds strong references to subscriber objects. If the publisher lives longer than the subscriber and the subscriber never unsubscribes, the subscriber stays reachable and is never collected."),
("Intermediate","What happens if an event handler throws an exception?","The invocation stops at that handler; later handlers don't run and the exception propagates to the code that raised the event. To isolate handlers, iterate <code>GetInvocationList()</code> and wrap each call in try/catch."),
("Intermediate","What is a multicast delegate and what's the return value when it has several methods?","A delegate with multiple methods in its invocation list, built with +=. Invoking calls each in order; for non-void delegates only the last method's return value is returned.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project 3: Bank account simulator with events",
"Build a bank simulator using records for transactions, enums for types, an abstract account hierarchy, pattern matching for statements, and events for low-balance and large-transaction alerts. Budget: about 4 hours.",
[("Ledger","The ordered list of transactions that explains how a balance was reached."),
("Minimum balance","The amount a savings account must keep; going below it triggers an alert or fee."),
("Overdraft","Permission for a current account to go below zero, up to a limit."),
("Alert threshold","A value that triggers an event when crossed.")],
["Transactions are immutable records; the ledger only grows.",
"Account is abstract; SavingsAccount and CurrentAccount decide how much can be withdrawn.",
"Events announce LowBalance and LargeTransaction; the console app decides what to do.",
"Statements use pattern matching on transaction type.",
"Tomorrow replaces generic exceptions with a custom exception hierarchy."],
f'''
<h3>Requirements</h3>
<ul>
<li><b>Savings account:</b> minimum balance ₹1,000, 3.5% annual interest credited monthly, withdrawal can't go below the minimum.</li>
<li><b>Current account:</b> overdraft limit (e.g. ₹10,000); no interest.</li>
<li>Every operation adds an immutable <code>Transaction</code> record.</li>
<li>Events: <code>LowBalance</code> when the balance drops below a threshold; <code>LargeTransaction</code> for any single amount ≥ ₹50,000.</li>
<li>A <code>Bank</code> class opens accounts and transfers between them.</li>
<li>Console menu: open, deposit, withdraw, transfer, statement, apply interest, list accounts.</li>
</ul>

<h3>Scaffold</h3>
{C(r"""
dotnet new sln -n Bank
dotnet new classlib -n Bank.Core
dotnet new console  -n Bank.App
dotnet sln add Bank.Core Bank.App
dotnet add Bank.App reference Bank.Core
rm Bank.Core/Class1.cs
""", lang="bash")}
{C(r"""
Bank/
├─ Bank.Core/
│  ├─ TransactionType.cs
│  ├─ Transaction.cs
│  ├─ AccountEvents.cs
│  ├─ Account.cs
│  ├─ SavingsAccount.cs
│  ├─ CurrentAccount.cs
│  └─ BankService.cs
└─ Bank.App/
   ├─ ConsoleInput.cs      (from Week 2)
   └─ Program.cs
""", lang="text")}

<h3>Step 1 — Transaction type and record</h3>
{C(r"""
namespace Bank.Core;

public enum TransactionType
{
    Deposit = 1,
    Withdrawal = 2,
    TransferIn = 3,
    TransferOut = 4,
    Interest = 5,
    Fee = 6
}

public readonly record struct Transaction(
    Guid Id,
    DateTime At,
    TransactionType Type,
    decimal Amount,
    decimal BalanceAfter,
    string? Note = null)
{
    public bool IsCredit => Type is TransactionType.Deposit or TransactionType.TransferIn or TransactionType.Interest;
}
""", "Bank.Core/Transaction.cs")}

<h3>Step 2 — Event arguments</h3>
{C(r"""
namespace Bank.Core;

public class LowBalanceEventArgs(string accountNumber, decimal balance, decimal threshold) : EventArgs
{
    public string AccountNumber { get; } = accountNumber;
    public decimal Balance { get; } = balance;
    public decimal Threshold { get; } = threshold;
}

public class LargeTransactionEventArgs(string accountNumber, Transaction transaction) : EventArgs
{
    public string AccountNumber { get; } = accountNumber;
    public Transaction Transaction { get; } = transaction;
}
""", "Bank.Core/AccountEvents.cs")}

<h3>Step 3 — Abstract account</h3>
{C(r"""
namespace Bank.Core;

public abstract class Account
{
    public const decimal LargeTransactionLimit = 50_000m;
    private static int _sequence = 1000;
    private readonly List<Transaction> _ledger = [];

    public string Number { get; }
    public string Holder { get; }
    public decimal Balance { get; private set; }
    public decimal LowBalanceThreshold { get; set; }
    public IReadOnlyList<Transaction> Ledger => _ledger.AsReadOnly();

    public event EventHandler<LowBalanceEventArgs>? LowBalance;
    public event EventHandler<LargeTransactionEventArgs>? LargeTransaction;

    protected Account(string prefix, string holder, decimal lowBalanceThreshold)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(holder);
        Number = $"{prefix}{++_sequence}";
        Holder = holder.Trim();
        LowBalanceThreshold = lowBalanceThreshold;
    }

    public abstract string Kind { get; }

    /// <summary>The most this account allows to be withdrawn right now.</summary>
    public abstract decimal AvailableToWithdraw { get; }

    public void Deposit(decimal amount, string? note = null) =>
        Credit(TransactionType.Deposit, amount, note);

    public void Withdraw(decimal amount, string? note = null) =>
        Debit(TransactionType.Withdrawal, amount, note);

    internal void Credit(TransactionType type, decimal amount, string? note)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(amount);
        Balance += amount;
        Record(type, amount, note);
    }

    internal void Debit(TransactionType type, decimal amount, string? note)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(amount);
        if (amount > AvailableToWithdraw)
            throw new InvalidOperationException(
                $"{Number}: can't withdraw {amount:N2}; available {AvailableToWithdraw:N2}");   // replaced tomorrow

        Balance -= amount;
        Record(type, amount, note);

        if (Balance < LowBalanceThreshold)
            OnLowBalance(new LowBalanceEventArgs(Number, Balance, LowBalanceThreshold));
    }

    private void Record(TransactionType type, decimal amount, string? note)
    {
        var tx = new Transaction(Guid.NewGuid(), DateTime.Now, type, amount, Balance, note);
        _ledger.Add(tx);
        if (amount >= LargeTransactionLimit)
            OnLargeTransaction(new LargeTransactionEventArgs(Number, tx));
    }

    protected virtual void OnLowBalance(LowBalanceEventArgs e) => LowBalance?.Invoke(this, e);
    protected virtual void OnLargeTransaction(LargeTransactionEventArgs e) => LargeTransaction?.Invoke(this, e);

    public override string ToString() => $"{Number}  {Kind,-8} {Holder,-12} {Balance,14:N2}";
}
""", "Bank.Core/Account.cs")}

<h3>Step 4 — Savings and current accounts</h3>
{C(r"""
namespace Bank.Core;

public class SavingsAccount : Account
{
    public const decimal MinimumBalance = 1_000m;
    public decimal AnnualInterestRate { get; }

    public SavingsAccount(string holder, decimal annualInterestRate = 0.035m)
        : base("SB", holder, lowBalanceThreshold: 2_000m)
    {
        AnnualInterestRate = annualInterestRate;
    }

    public override string Kind => "Savings";
    public override decimal AvailableToWithdraw => Math.Max(0, Balance - MinimumBalance);

    public decimal ApplyMonthlyInterest()
    {
        decimal interest = Math.Round(Balance * AnnualInterestRate / 12, 2);
        if (interest > 0) Credit(TransactionType.Interest, interest, $"{AnnualInterestRate:P1} p.a.");
        return interest;
    }
}
""", "Bank.Core/SavingsAccount.cs")}
{C(r"""
namespace Bank.Core;

public class CurrentAccount : Account
{
    public decimal OverdraftLimit { get; }

    public CurrentAccount(string holder, decimal overdraftLimit = 10_000m)
        : base("CA", holder, lowBalanceThreshold: 0m)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(overdraftLimit);
        OverdraftLimit = overdraftLimit;
    }

    public override string Kind => "Current";
    public override decimal AvailableToWithdraw => Balance + OverdraftLimit;
}
""", "Bank.Core/CurrentAccount.cs")}

<h3>Step 5 — BankService</h3>
{C(r"""
namespace Bank.Core;

public class BankService
{
    private readonly Dictionary<string, Account> _accounts = new(StringComparer.OrdinalIgnoreCase);

    public IReadOnlyCollection<Account> Accounts => _accounts.Values;

    // Forward every account's events through the bank so the app subscribes once
    public event EventHandler<LowBalanceEventArgs>? LowBalance;
    public event EventHandler<LargeTransactionEventArgs>? LargeTransaction;

    public T Open<T>(T account) where T : Account
    {
        account.LowBalance += (s, e) => LowBalance?.Invoke(s, e);
        account.LargeTransaction += (s, e) => LargeTransaction?.Invoke(s, e);
        _accounts.Add(account.Number, account);
        return account;
    }

    public Account Get(string number) =>
        _accounts.TryGetValue(number, out var acc)
            ? acc
            : throw new KeyNotFoundException($"No account {number}");   // replaced tomorrow

    public void Transfer(string fromNumber, string toNumber, decimal amount)
    {
        if (string.Equals(fromNumber, toNumber, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Can't transfer to the same account");

        Account from = Get(fromNumber), to = Get(toNumber);
        from.Debit(TransactionType.TransferOut, amount, $"to {to.Number}");   // throws first if not enough
        to.Credit(TransactionType.TransferIn, amount, $"from {from.Number}");
    }
}
""", "Bank.Core/BankService.cs")}
<p>The generic <code>Open&lt;T&gt;</code> method is a preview of Week 4: it returns the exact subtype you passed in.</p>

<h3>Step 6 — Statement with pattern matching</h3>
{C(r"""
static void PrintStatement(Account acc)
{
    Console.WriteLine($"\n  Statement for {acc.Number} ({acc.Holder})");
    Console.WriteLine($"  {"Date",-17}{"Description",-26}{"Debit",12}{"Credit",12}{"Balance",14}");

    foreach (var tx in acc.Ledger)
    {
        string description = tx switch
        {
            { Type: TransactionType.Deposit, Amount: >= Account.LargeTransactionLimit } => "Large deposit",
            { Type: TransactionType.Deposit }     => "Deposit",
            { Type: TransactionType.Withdrawal }  => "ATM / withdrawal",
            { Type: TransactionType.TransferIn, Note: var n }  => $"Transfer {n}",
            { Type: TransactionType.TransferOut, Note: var n } => $"Transfer {n}",
            { Type: TransactionType.Interest }    => "Interest credited",
            { Type: TransactionType.Fee }         => "Charges",
            _ => tx.Type.ToString()
        };

        string debit  = tx.IsCredit ? "" : tx.Amount.ToString("N2");
        string credit = tx.IsCredit ? tx.Amount.ToString("N2") : "";
        Console.WriteLine($"  {tx.At,-17:dd MMM yyyy HH:mm}{description,-26}{debit,12}{credit,12}{tx.BalanceAfter,14:N2}");
    }
}
""", "Bank.App/Statement.cs (local function in Program.cs)")}

<h3>Step 7 — Program.cs</h3>
{C(r"""
using Bank.App;
using Bank.Core;

var bank = new BankService();

bank.LowBalance += (_, e) =>
{
    Console.ForegroundColor = ConsoleColor.Yellow;
    Console.WriteLine($"  ⚠ Low balance on {e.AccountNumber}: {e.Balance:N2} (alert below {e.Threshold:N2})");
    Console.ResetColor();
};
bank.LargeTransaction += (_, e) =>
    Console.WriteLine($"  🔔 Large {e.Transaction.Type} of {e.Transaction.Amount:N2} on {e.AccountNumber}");

// Seed two accounts
var sb = bank.Open(new SavingsAccount("Samrath"));
sb.Deposit(25_000m, "Opening deposit");
var ca = bank.Open(new CurrentAccount("Ugaav Labs", overdraftLimit: 20_000m));
ca.Deposit(60_000m, "Capital");

int choice;
do
{
    Console.WriteLine(QQQ

        ===== Bank Simulator =====
        1) List accounts      5) Transfer
        2) Open account       6) Statement
        3) Deposit            7) Apply monthly interest
        4) Withdraw           0) Exit
        QQQ);
    choice = ConsoleInput.ReadChoice("Choose: ", 0, 7);

    try
    {
        switch (choice)
        {
            case 1: foreach (var a in bank.Accounts) Console.WriteLine($"  {a}"); break;
            case 2: OpenAccount(); break;
            case 3: bank.Get(ConsoleInput.ReadText("Account: ")).Deposit(ConsoleInput.ReadDecimal("Amount: ")); break;
            case 4: bank.Get(ConsoleInput.ReadText("Account: ")).Withdraw(ConsoleInput.ReadDecimal("Amount: ")); break;
            case 5: bank.Transfer(ConsoleInput.ReadText("From: "), ConsoleInput.ReadText("To: "), ConsoleInput.ReadDecimal("Amount: ")); break;
            case 6: PrintStatement(bank.Get(ConsoleInput.ReadText("Account: "))); break;
            case 7:
                foreach (var s in bank.Accounts.OfType<SavingsAccount>())
                    Console.WriteLine($"  {s.Number}: +{s.ApplyMonthlyInterest():N2}");
                break;
        }
    }
    catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or KeyNotFoundException)
    {
        Console.WriteLine($"  ✗ {ex.Message}");
    }
} while (choice != 0);

void OpenAccount()
{
    string holder = ConsoleInput.ReadText("Holder name: ");
    Account acc = ConsoleInput.ReadChoice("1) Savings  2) Current: ", 1, 2) == 1
        ? bank.Open(new SavingsAccount(holder))
        : bank.Open(new CurrentAccount(holder));
    Console.WriteLine($"  ✓ Opened {acc.Number}");
}

// PrintStatement(...) from Step 6 goes here
""", "Bank.App/Program.cs")}
<p>Add <code>ReadDecimal</code> to ConsoleInput: same as ReadDouble, but with <code>decimal.TryParse</code> and a check for <code>&gt; 0</code>.</p>

<h3>Run it</h3>
{C(r"""
Choose: 4
Account: SB1001
Amount: 23000
Choose: 4                               (balance is now 2,000.00: not below the threshold, no alert)
Account: sb1001
Amount: 500
  ⚠ Low balance on SB1001: 1,500.00 (alert below 2,000.00)
Choose: 4
Account: SB1001
Amount: 1000
  ✗ SB1001: can't withdraw 1,000.00; available 500.00
""", lang="text")}

<h3>Stretch goals</h3>
<ul>
<li>Charge a ₹50 <code>Fee</code> transaction whenever a savings balance drops below the minimum at month end.</li>
<li>Add a <code>FixedDeposit</code> account that blocks withdrawals until a maturity date.</li>
<li>Write the statement to a text file.</li>
</ul>
''',
iqs=[("Basic","Why is Transaction a readonly record struct?","Transactions are small, immutable facts that never change once recorded. A readonly record struct gives value equality and a readable ToString without heap allocation per transaction."),
("Basic","Why does Account use events instead of printing alerts itself?","Separation of concerns: the domain only announces that something happened. The console app, an email service or a fraud check can subscribe without the account knowing about them."),
("Intermediate","Why does Transfer debit before crediting?","Debit validates funds and throws if insufficient. Doing it first means a failed transfer never credits the receiver, keeping both accounts consistent. Real systems use database transactions for this (Week 13)."),
("Intermediate","How does polymorphism decide how much can be withdrawn?","AvailableToWithdraw is abstract: savings returns balance minus the minimum, current returns balance plus the overdraft. Debit only calls the abstract property, so new account types plug in without changing it.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Custom exceptions for the bank, README, push and revision",
"Replace generic exceptions with a domain exception hierarchy, handle them precisely in the app, document the project and revise the week.",
[("Exception hierarchy","A family of exceptions sharing a base class, so callers can catch broadly or narrowly."),
("Domain exception","An exception expressing a business rule violation, e.g. insufficient funds."),
("Frozen account","An account blocked from debits, e.g. after suspected fraud."),
("Daily limit","The maximum total amount that may be withdrawn per day.")],
["One abstract base (<code>BankException</code>) lets the app catch all business errors in one place.",
"Each subtype carries the data a handler needs (shortfall, limit, account number).",
"The app catches specific types for specific messages, then the base type as a fallback.",
"Programming bugs (ArgumentException from wrong code) are separate from business failures."],
f'''
<h3>1. Exception hierarchy</h3>
{C(r"""
namespace Bank.Core.Exceptions;

public abstract class BankException : Exception
{
    public string? AccountNumber { get; }
    protected BankException(string message, string? accountNumber = null, Exception? inner = null)
        : base(message, inner) => AccountNumber = accountNumber;
}

public sealed class AccountNotFoundException(string accountNumber)
    : BankException($"Account {accountNumber} doesn't exist", accountNumber);

public sealed class InsufficientFundsException(string accountNumber, decimal requested, decimal available)
    : BankException($"{accountNumber}: requested {requested:N2}, available {available:N2}", accountNumber)
{
    public decimal Requested { get; } = requested;
    public decimal Available { get; } = available;
    public decimal Shortfall => Requested - Available;
}

public sealed class AccountFrozenException(string accountNumber, string reason)
    : BankException($"{accountNumber} is frozen: {reason}", accountNumber)
{
    public string Reason { get; } = reason;
}

public sealed class DailyLimitExceededException(string accountNumber, decimal limit, decimal usedToday)
    : BankException($"{accountNumber}: daily limit {limit:N2} reached (used {usedToday:N2})", accountNumber)
{
    public decimal Limit { get; } = limit;
    public decimal UsedToday { get; } = usedToday;
}
""", "Bank.Core/Exceptions/BankExceptions.cs")}

<h3>2. Use them in Account</h3>
{C(r"""
// Account.cs — new members
public const decimal DailyWithdrawalLimit = 100_000m;
public bool IsFrozen { get; private set; }
public string? FrozenReason { get; private set; }

public void Freeze(string reason) { IsFrozen = true; FrozenReason = reason; }
public void Unfreeze() { IsFrozen = false; FrozenReason = null; }

private decimal WithdrawnToday() =>
    Ledger.Where(t => t.At.Date == DateTime.Today &&
                      t.Type is TransactionType.Withdrawal or TransactionType.TransferOut)
          .Sum(t => t.Amount);

internal void Debit(TransactionType type, decimal amount, string? note)
{
    ArgumentOutOfRangeException.ThrowIfNegativeOrZero(amount);       // caller bug → ArgumentException

    if (IsFrozen)
        throw new AccountFrozenException(Number, FrozenReason ?? "no reason given");

    decimal used = WithdrawnToday();
    if (used + amount > DailyWithdrawalLimit)
        throw new DailyLimitExceededException(Number, DailyWithdrawalLimit, used);

    if (amount > AvailableToWithdraw)
        throw new InsufficientFundsException(Number, amount, AvailableToWithdraw);

    Balance -= amount;
    Record(type, amount, note);
    if (Balance < LowBalanceThreshold)
        OnLowBalance(new LowBalanceEventArgs(Number, Balance, LowBalanceThreshold));
}
""", "Bank.Core/Account.cs (changes)")}
{C(r"""
// BankService.cs
public Account Get(string number) =>
    _accounts.TryGetValue(number, out var acc) ? acc : throw new AccountNotFoundException(number);
""")}

<h3>3. Handle them precisely in the app</h3>
{C(r"""
try
{
    // ... switch (choice) as before, plus:
    // case 8: bank.Get(ConsoleInput.ReadText("Account: ")).Freeze(ConsoleInput.ReadText("Reason: ")); break;
}
catch (InsufficientFundsException ex)
{
    Console.WriteLine($"  ✗ Not enough money. You're short by {ex.Shortfall:N2}.");
}
catch (DailyLimitExceededException ex)
{
    Console.WriteLine($"  ✗ Daily limit of {ex.Limit:N2} reached. Try again tomorrow.");
}
catch (AccountFrozenException ex)
{
    Console.WriteLine($"  ✗ Account frozen ({ex.Reason}). Contact your branch.");
}
catch (BankException ex)                                  // any other business rule
{
    Console.WriteLine($"  ✗ {ex.Message}");
}
catch (ArgumentException ex)                              // bad input that slipped through
{
    Console.WriteLine($"  ✗ Invalid input: {ex.Message}");
}
""", "Bank.App/Program.cs (catch blocks)")}
{tip("Notice the order: specific subclasses first, then <code>BankException</code>, then framework types. Reversing them is a compile error.")}

<h3>4. Try to break it</h3>
{table(["Scenario","Expected"],[
["Withdraw 24,500 from SB with 25,000","InsufficientFunds: short by 500 (minimum balance 1,000)"],
["Current account with 60,000 and 20,000 overdraft: withdraw 80,000","Succeeds, balance −20,000, large-transaction alert"],
["Withdraw 60,000 then 50,000 the same day","DailyLimitExceeded on the second"],
["Freeze SB, then deposit","Allowed (only debits are blocked)"],
["Freeze SB, then withdraw","AccountFrozen with the reason"],
["Transfer to unknown account XX9999","AccountNotFound"],
["Transfer SB1001 → SB1001","\"Can't transfer to the same account\""],
["Deposit −500","Invalid input (ArgumentOutOfRange)"]])}

<h3>5. README and push</h3>
{C(r"""
# Bank Simulator

Micro-project 3 of my .NET full-stack roadmap (Week 3: modern C# and exceptions).

## Features
- Savings (minimum balance, monthly interest) and current (overdraft) accounts
- Immutable ledger of `Transaction` records; formatted statements
- Events: low-balance and large-transaction alerts
- Transfers between accounts
- Domain exceptions: insufficient funds, daily limit, frozen account, account not found

## C# features used
records / record structs, enums, pattern matching (property, relational, logical),
events with EventHandler<T>, custom exception hierarchy, exception filters, generics preview

## Run
```bash
dotnet run --project Bank.App
```
""", "README.md", lang="markdown")}
{C(r"""
git add .
git commit -m "Bank: accounts, ledger, events, domain exceptions"
git push
""", lang="bash")}

<h3>6. Week 3 revision checklist</h3>
<ul>
<li>struct vs class vs record vs record struct vs tuple — when to use each</li>
<li>with-expressions are shallow; positional records generate Deconstruct</li>
<li>All pattern kinds, with one example each; tuple-switch state machines</li>
<li>Enums: TryParse, IsDefined, explicit values; [Flags] with powers of two</li>
<li>Equals/GetHashCode contract; IEquatable&lt;T&gt;; boxing and where it hides</li>
<li>try/catch/finally order; filters; throw vs throw ex; inner exceptions; custom exceptions</li>
<li>Delegates, Func/Action, multicast; events, EventHandler&lt;T&gt;, leaks</li>
</ul>

<h3>7. Quick quiz — predict the output</h3>
<details><summary>Q1. What prints?</summary>
{C(r"""
record Point(int X, int Y);
var a = new Point(1, 2);
var b = a with { Y = 5 };
Console.WriteLine($"{a == new Point(1, 2)} {b}");
""")}<b>True Point {{ X = 1, Y = 5 }}</b>. Records compare by value, and with makes a modified copy.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
try { throw new InvalidOperationException("A"); }
catch (Exception) { Console.Write("1"); }
finally { Console.Write("2"); }
Console.Write("3");
""")}<b>123.</b> The catch handles it, finally always runs, then execution continues.</details>
<details><summary>Q3. Does this compile?</summary>
{C(r"""
try { }
catch (Exception) { }
catch (IOException) { }
""")}<b>No.</b> CS0160: the IOException block is unreachable because Exception already catches it.</details>
<details><summary>Q4. What prints?</summary>
{C(r"""
int[] xs = [3, 4];
Console.WriteLine(xs switch { [] => "empty", [_] => "one", [var a, var b] => $"{a + b}", _ => "many" });
""")}<b>7.</b> The two-element list pattern matches and binds a = 3, b = 4.</details>
<details><summary>Q5. What prints?</summary>
{C(r"""
Action a = () => Console.Write("x");
a += () => Console.Write("y");
a += () => Console.Write("x");
a();
""")}<b>xyx.</b> A multicast delegate invokes each method in the order added.</details>

<div class="note tip"><b>Next week:</b> Collections and generics — List, Dictionary, HashSet, Queue, Stack, generic classes and constraints, IEnumerable and yield, comparers, and immutable/frozen collections. You'll refactor the library project around a generic repository.</div>
''',
iqs=[("Basic","Why give custom exceptions a common base class?","Callers can catch the whole family with one catch (BankException) for generic handling, while still catching specific subtypes when they need special behaviour."),
("Basic","Should 'insufficient funds' be an exception or a result object?","Both are defensible. If callers usually check availability first, an attempted overdraw is a contract violation and an exception fits. If it's a common, expected outcome (e.g. API validation), a Result is cheaper and clearer. Be consistent within a layer."),
("Intermediate","How do you keep a stack trace when translating a low-level exception into a domain exception?","Pass the original as the inner exception: <code>throw new AccountNotFoundException(id, ex)</code>. Logs then show both the domain message and the original stack trace."),
("Intermediate","Why separate ArgumentException from BankException in the catch blocks?","ArgumentException signals a programming or input-validation bug (negative amount); BankException signals a legitimate business rule. Treating them differently helps users get the right message and helps developers spot real bugs.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Structs, records, tuples and deconstruction","Structs &amp; records","readonly structs, records and with, record structs, tuples, Deconstruct.","2 hrs"),
 (2,"TUE","Pattern matching in depth","Pattern matching","Property, relational, logical, positional and list patterns; state machines.","2 hrs"),
 (3,"WED","Enums, equality and boxing","Enums &amp; equality","Enums and flags, Equals/GetHashCode contract, IEquatable, hidden boxing.","2 hrs"),
 (4,"THU","Exceptions","Exceptions","try/catch/finally, filters, throw vs throw ex, custom exceptions, guards.","2 hrs"),
 (5,"FRI","Delegates and events","Delegates &amp; events","Delegates, Func/Action, multicast, EventHandler&lt;T&gt;, leaks.","2 hrs"),
 (6,"SAT","Micro-project 3: Bank simulator","Project: bank","Accounts, ledger records, low-balance and large-transaction events.","4 hrs"),
 (7,"SUN","Bank exceptions and revision","Exceptions &amp; revision","Domain exception hierarchy, precise catches, README, quiz.","4 hrs"),
]
build("/home/claude/build/week02.html", "/home/claude/build/week03.html", 3,
      "Week 3 — Modern C# and exceptions", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 3 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Micro-project 3"],
      "This week covers the features that make modern C# concise and safe: records, pattern matching and proper equality, plus how to handle failure with exceptions and how objects announce changes with events. You'll finish with a bank simulator that uses all of them.",
      cards, days)
print("built")
