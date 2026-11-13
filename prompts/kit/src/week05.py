import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Delegates in depth: Func, Action, Predicate, variance and higher-order functions",
"Go beyond Week 3's intro: understand what a delegate really is, use the built-in generic delegates fluently, know how method groups and variance convert, and use delegates as strategies, callbacks and function-returning functions.",
[("Delegate","A type-safe object that points to one or more methods with a specific signature. The compiler turns each delegate type into a sealed class deriving from <code>System.MulticastDelegate</code>."),
("Generic delegate","A delegate type with type parameters, e.g. <code>delegate TResult Transformer&lt;in T, out TResult&gt;(T input);</code>"),
("Func&lt;T1…T16, TResult&gt;","Built-in delegates for methods that return a value. The last type argument is the return type."),
("Action&lt;T1…T16&gt;","Built-in delegates for methods that return void."),
("Predicate&lt;T&gt;","A delegate <code>bool (T obj)</code>, used by <code>List&lt;T&gt;.FindAll</code>, <code>RemoveAll</code>, <code>Array.Exists</code>."),
("Comparison&lt;T&gt;","A delegate <code>int (T x, T y)</code> used by <code>List&lt;T&gt;.Sort</code> and <code>Array.Sort</code>."),
("Converter&lt;TIn,TOut&gt;","A delegate <code>TOut (TIn input)</code> used by <code>List.ConvertAll</code> and <code>Array.ConvertAll</code>."),
("Method group","A method name without parentheses, such as <code>int.Parse</code>. It may stand for several overloads."),
("Method group conversion","The compiler turning a method group into a delegate instance by picking the overload that matches the delegate's signature."),
("Target / Method","Properties on every delegate: the object the method runs on (null for static methods) and the <code>MethodInfo</code> it calls."),
("Invocation list","The ordered list of methods inside a multicast delegate, returned by <code>GetInvocationList()</code>."),
("Delegate variance","Return types may be more derived (covariance) and parameter types less derived (contravariance) than the delegate declares."),
("Callback","A delegate passed to a method so that the method can call your code back at the right moment."),
("Higher-order function","A function that takes a function as a parameter, returns one, or both."),
("Strategy (delegate style)","Swapping an algorithm by passing a different delegate instead of a different interface implementation.")],
["Prefer <code>Func</code>/<code>Action</code> over custom delegate types unless a name adds real meaning (e.g. <code>EventHandler</code>).",
"Two delegate types with identical signatures are still different types: <code>Predicate&lt;T&gt;</code> doesn't convert to <code>Func&lt;T,bool&gt;</code>.",
"A method group with several overloads has no natural type, so <code>var f = int.Parse;</code> doesn't compile.",
"Generic variance only works for reference types: <code>Func&lt;string&gt;</code> → <code>Func&lt;object&gt;</code> works, <code>Func&lt;int&gt;</code> → <code>Func&lt;object&gt;</code> doesn't.",
"A delegate to an instance method keeps that object alive for as long as the delegate is alive.",
"Delegates are the foundation of LINQ: every <code>Where</code>, <code>Select</code> and <code>OrderBy</code> takes a Func."],
f'''
<h3>1. What a delegate really is</h3>
<p>When you declare a delegate type, the compiler generates a sealed class with an <code>Invoke</code> method that has your signature. A delegate instance stores two things: the <b>method</b> to call and the <b>target</b> object to call it on. Calling <code>d(x)</code> is shorthand for <code>d.Invoke(x)</code>.</p>
{C(r"""
// Statements first (top-level program), type declarations at the bottom
Transformer<decimal, decimal> gst = Pricing.AddGst;
Console.WriteLine(gst(1000m));                    // 1180.00
Console.WriteLine(gst.Invoke(500m));              // 590.00 — identical to gst(500m)

Console.WriteLine(gst.GetType().BaseType);        // System.MulticastDelegate
Console.WriteLine(gst.Method.Name);               // AddGst
Console.WriteLine(gst.Target is null);            // True — static methods have no target

var cart = new Cart();
cart.Add(1_499m);
Func<decimal> total = cart.Total;                 // instance method: the delegate remembers `cart`
cart.Add(250m);
Console.WriteLine(total());                       // 1749 — it calls Total() on the live object
Console.WriteLine(ReferenceEquals(total.Target, cart));   // True

// A custom generic delegate with variance annotations (more on `in`/`out` below)
public delegate TResult Transformer<in T, out TResult>(T input);

public static class Pricing
{
    public static decimal AddGst(decimal amount) => amount * 1.18m;
}

public class Cart
{
    private readonly List<decimal> _items = [];
    public void Add(decimal price) => _items.Add(price);
    public decimal Total() => _items.Sum();
}
""", "DelegateAnatomy.cs")}
{tip("In a top-level <code>Program.cs</code>, statements must come before any type declarations (error CS8803 otherwise). In real projects, put types in their own files.")}

<h3>2. The built-in delegate family</h3>
{C(r"""
var orders = new List<Order>
{
    new(1, "Asha", 12_500m),
    new(2, "Ravi", 899m),
    new(3, "Meena", 45_000m)
};

Func<decimal, decimal, decimal> applyDiscount = (price, pct) => price - price * pct / 100;
Action<string, decimal> printLine = (label, amount) => Console.WriteLine($"{label,-10}{amount,12:N2}");
Predicate<Order> isHighValue = o => o.Amount >= 10_000m;
Comparison<Order> byAmountDesc = (a, b) => b.Amount.CompareTo(a.Amount);
Converter<Order, string> toLabel = o => $"#{o.Id} {o.Customer}";

List<Order> big = orders.FindAll(isHighValue);           // List<T> APIs (2005-era) use Predicate<T>…
orders.Sort(byAmountDesc);                               // …Comparison<T>…
List<string> labels = orders.ConvertAll(toLabel);        // …and Converter<TIn,TOut>
IEnumerable<Order> big2 = orders.Where(o => o.Amount >= 10_000m);   // LINQ uses Func<T,bool>

printLine("Discounted", applyDiscount(45_000m, 10));     // Discounted   40,500.00
Console.WriteLine(string.Join(", ", labels));            // #3 Meena, #1 Asha, #2 Ravi

// Func<Order, bool> f = isHighValue;      // ❌ CS0029: different delegate types, same signature
// orders.Where(isHighValue);              // ❌ same reason
Func<Order, bool> f = isHighValue.Invoke;  // ✓ method group conversion of Invoke
Func<Order, bool> g = new Func<Order, bool>(isHighValue);   // ✓ explicit delegate creation also works

public record Order(int Id, string Customer, decimal Amount);
""", "BuiltInDelegates.cs")}
{table(["Delegate","Signature","Typical users"],[
["<code>Action</code> … <code>Action&lt;T1..T16&gt;</code>","<code>void (T1, …)</code>","Callbacks, <code>List.ForEach</code>, <code>Task.Run</code>"],
["<code>Func&lt;TResult&gt;</code> … <code>Func&lt;T1..T16, TResult&gt;</code>","<code>TResult (T1, …)</code>","LINQ, factories, strategies"],
["<code>Predicate&lt;T&gt;</code>","<code>bool (T)</code>","<code>List.FindAll/RemoveAll/Exists</code>, <code>Array.Find</code>"],
["<code>Comparison&lt;T&gt;</code>","<code>int (T, T)</code>","<code>List.Sort</code>, <code>Comparer&lt;T&gt;.Create</code>"],
["<code>Converter&lt;TIn,TOut&gt;</code>","<code>TOut (TIn)</code>","<code>List.ConvertAll</code>, <code>Array.ConvertAll</code>"],
["<code>EventHandler&lt;TArgs&gt;</code>","<code>void (object?, TArgs)</code>","Events (Week 3)"]])}

<h3>3. Method group conversion and natural types</h3>
<p>You rarely need a lambda that only forwards its arguments. Pass the method group and the compiler picks the overload that matches the delegate the parameter expects. Since C# 10, lambdas and method groups with a single candidate also have a <b>natural type</b>, so <code>var</code> works.</p>
{C(r"""
string[] rawQty = ["120", "45", "980"];
int[] qty = Array.ConvertAll(rawQty, int.Parse);        // picks int.Parse(string) — no lambda needed
List<string> cities = ["Pune", "Indore", "Kochi"];
cities.ForEach(Console.WriteLine);                       // picks Console.WriteLine(string)

// Same thing written with forwarding lambdas — works, but noisier
int[] qty2 = Array.ConvertAll(rawQty, s => int.Parse(s));

// Natural types (C# 10+)
var addGst = Pricing.AddGst;                     // Func<decimal, decimal> — only one AddGst exists
var label = (Order o) => $"#{o.Id}";             // Func<Order, string>
var log = (string msg) => Console.WriteLine(msg);// Action<string>
// var parse = int.Parse;                        // ❌ CS8917: several overloads, delegate type can't be inferred
// var square = x => x * x;                      // ❌ CS8917: parameter type unknown

Func<string, int> parse = int.Parse;             // ✓ the target type picks the overload
""")}
{warn("Every method group conversion to an <b>instance</b> method creates a new delegate object. Inside a hot loop, create the delegate once outside the loop. (Since C# 11 the compiler caches conversions of <i>static</i> method groups, as it always has for non-capturing lambdas.)", "Note")}

<h3>4. Delegate variance</h3>
<p>Variance answers: \"can I use a delegate built for one type where another is expected?\" It works in two places: when converting a <b>method group</b> to a delegate, and between <b>generic delegate types</b> whose type parameters are marked <code>out</code> (covariant) or <code>in</code> (contravariant). <code>Func</code> is declared <code>Func&lt;in T, out TResult&gt;</code> and <code>Action</code> is <code>Action&lt;in T&gt;</code>.</p>
{C(r"""
// 1. Generic variance between delegate types
Func<UpiPayment> makeUpi = () => new UpiPayment(499m, "asha@okaxis");
Func<Payment> makeAny = makeUpi;            // ✓ covariance: something that produces UPI produces a Payment

Action<Payment> audit = p => Console.WriteLine($"Audit ₹{p.Amount:N2}");
Action<UpiPayment> auditUpi = audit;        // ✓ contravariance: anything that handles any Payment handles UPI

// 2. Method-group variance (works even for non-generic delegate types)
PaymentFactory factory = CreateCard;        // ✓ method returns CardPayment; delegate promises Payment
PaymentHandler handler = LogAnyPayment;     // ✓ method accepts Payment; delegate passes CardPayment

handler(factory() as CardPayment ?? new CardPayment(0, "0000"));   // Logged ₹1,250.00

// 3. Where variance stops
// Func<int> one = () => 1;
// Func<object> boxed = one;                // ❌ variance is reference-types only (int would need boxing)
// Factory<UpiPayment> f1 = ...;
// Factory<Payment> f2 = f1;                // ❌ Factory<T> has no `out`, so it's invariant

static CardPayment CreateCard() => new(1_250m, "4242");
static void LogAnyPayment(Payment p) => Console.WriteLine($"Logged ₹{p.Amount:N2}");

delegate Payment PaymentFactory();
delegate void PaymentHandler(CardPayment payment);
delegate T Factory<T>();                    // invariant: no in/out annotation

abstract record Payment(decimal Amount);
record UpiPayment(decimal Amount, string Vpa) : Payment(Amount);
record CardPayment(decimal Amount, string Last4) : Payment(Amount);
""", "Variance.cs")}
{table(["Direction","Keyword","Rule of thumb","Example"],[
["Covariance","<code>out</code>","Outputs can be <i>more specific</i> than promised","<code>Func&lt;UpiPayment&gt;</code> → <code>Func&lt;Payment&gt;</code>"],
["Contravariance","<code>in</code>","Inputs can be <i>more general</i> than required","<code>Action&lt;Payment&gt;</code> → <code>Action&lt;UpiPayment&gt;</code>"],
["Invariance","(none)","Exact type only","<code>Factory&lt;UpiPayment&gt;</code> ↛ <code>Factory&lt;Payment&gt;</code>"]])}
{warn("Variance gives you a different <i>static</i> type, not a different runtime type. <code>Action&lt;string&gt; a = someActionOfObject; a += otherActionOfString;</code> compiles but throws <code>ArgumentException</code> at runtime because <code>Delegate.Combine</code> needs identical runtime types.", "Gotcha")}

<h3>5. Delegates as strategies</h3>
<p>In Week 2 you used an interface for each interchangeable behaviour. When the behaviour is a single method with no state, a delegate is lighter: no class per variant, and the strategies can live in a dictionary.</p>
{C(r"""
// Shipping cost strategies: weight in kg → charge in ₹
var shippingRules = new Dictionary<string, Func<decimal, decimal>>(StringComparer.OrdinalIgnoreCase)
{
    ["standard"] = kg => 40m + 15m * kg,
    ["express"]  = kg => 99m + 25m * kg,
    ["pickup"]   = _ => 0m,
};

decimal Quote(string method, decimal kg) =>
    shippingRules.TryGetValue(method, out var rule)
        ? rule(kg)
        : throw new ArgumentException($"Unknown shipping method '{method}'");

Console.WriteLine(Quote("express", 2m));     // 149
Console.WriteLine(Quote("Standard", 2m));    // 70

// A pipeline of pricing rules applied in order
var rules = new List<Func<decimal, decimal>>
{
    p => p >= 5_000m ? p * 0.90m : p,        // 10% off orders ≥ ₹5,000
    p => p - 200m,                           // festive coupon
    p => Math.Round(p * 1.18m, 2)            // GST last
};

decimal price = 6_000m;
foreach (var rule in rules) price = rule(price);
Console.WriteLine(price);                    // 6136.00
""", "Strategies.cs")}
{table(["","Interface strategy","Delegate strategy"],[
["Code per variant","A class","A lambda or method"],
["Holds state / config","Naturally (fields, DI)","Through closures (tomorrow)"],
["Several related operations","Yes, one interface groups them","One delegate per operation"],
["Discoverable / named","Yes — <code>IShippingCalculator</code>","Less — just a Func"],
["Best when","Real dependencies, multiple methods, DI","Small, stateless, swap-at-runtime rules"]])}

<h3>6. Callbacks and higher-order functions</h3>
<p>A higher-order function takes or returns functions. You use them every day (<code>Where</code> takes a function); writing your own removes repetition such as retry loops, timing and caching.</p>
{C(r"""
namespace Toolkit.Functional;

public static class Fn
{
    // Takes a function, returns a function that caches results
    public static Func<T, TResult> Memoize<T, TResult>(Func<T, TResult> f) where T : notnull
    {
        var cache = new Dictionary<T, TResult>();
        return x => cache.TryGetValue(x, out var hit) ? hit : cache[x] = f(x);
    }

    // Composition: first, then second (an extension method — Tuesday)
    public static Func<T, TOut> Then<T, TMid, TOut>(this Func<T, TMid> first, Func<TMid, TOut> second) =>
        x => second(first(x));

    // Callback: the caller decides what to do on each failed attempt
    public static T Retry<T>(Func<T> operation, int attempts, Action<int, Exception>? onRetry = null)
    {
        for (int attempt = 1; ; attempt++)
        {
            try { return operation(); }
            catch (Exception ex) when (attempt < attempts)
            {
                onRetry?.Invoke(attempt, ex);
            }
        }
    }

    public static TimeSpan Time(Action work)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        work();
        return sw.Elapsed;
    }
}
""", "Toolkit/Functional/Fn.cs")}
{C(r"""
using Toolkit.Functional;

// Memoize: an expensive delivery-rate lookup by PIN code
Func<string, decimal> slowRate = pin =>
{
    Console.WriteLine($"  (looking up {pin}…)");
    return pin.StartsWith('4') ? 60m : 45m;
};
var rate = Fn.Memoize(slowRate);
Console.WriteLine(rate("411001"));    //   (looking up 411001…)  then 60
Console.WriteLine(rate("411001"));    // 60 — cached, no lookup message

// Compose
Func<decimal, decimal> withGst = p => p * 1.18m;
var finalPrice = withGst.Then(p => Math.Round(p, 0));
Console.WriteLine(finalPrice(849m));  // 1002

// Retry with a callback
int calls = 0;
string status = Fn.Retry(() =>
{
    if (++calls < 3) throw new HttpRequestException("Gateway timeout");
    return "PAID";
}, attempts: 5, onRetry: (n, ex) => Console.WriteLine($"  attempt {n} failed: {ex.Message}"));
Console.WriteLine(status);
//   attempt 1 failed: Gateway timeout
//   attempt 2 failed: Gateway timeout
// PAID

Console.WriteLine(Fn.Time(() => Thread.Sleep(50)).TotalMilliseconds >= 50);   // True
""", "Program.cs")}
{tip("The exception filter <code>when (attempt &lt; attempts)</code> lets the last failure propagate with its original stack trace — no rethrow needed.")}
''',
["Writing <code>x =&gt; Foo(x)</code> when the method group <code>Foo</code> would do.",
"Expecting <code>Predicate&lt;T&gt;</code> and <code>Func&lt;T,bool&gt;</code> to be interchangeable.",
"Expecting variance to work with value types (<code>Func&lt;int&gt;</code> → <code>Func&lt;object&gt;</code>).",
"Combining (<code>+=</code>) variant delegates of different runtime types and getting an ArgumentException.",
"Keeping a delegate to an instance method in a static field, which keeps the whole object alive (a leak)."],
("40 min", ["Write <code>static List&lt;T&gt; Filter&lt;T&gt;(IEnumerable&lt;T&gt; items, Func&lt;T, bool&gt; keep)</code> and <code>Map&lt;T, TOut&gt;</code> by hand (no LINQ). Use them on a list of employees to get names of people earning above ₹8 LPA.",
"Build a <code>Dictionary&lt;string, Func&lt;decimal, decimal, decimal&gt;&gt;</code> calculator (+, −, ×, ÷) and plug it into your Week 1 Toolkit calculator instead of the switch.",
"Write <code>Fn.Memoize</code> for a slow Fibonacci and compare timings for n = 40 with and without memoization using <code>Fn.Time</code>."]),
[("What two things does a delegate instance store?","The method to call (<code>Method</code>) and the object to call it on (<code>Target</code>, null for static methods). Multicast delegates hold an invocation list of such pairs."),
("Why doesn't <code>var f = int.Parse;</code> compile?","int.Parse has several overloads, so the method group has no single natural type. Give it a target type: <code>Func&lt;string, int&gt; f = int.Parse;</code>"),
("Can <code>Action&lt;object&gt;</code> be assigned to <code>Action&lt;string&gt;</code>?","Yes. Action's parameter is contravariant (<code>in T</code>): a handler that accepts any object can certainly accept a string.")],
[("Basic","What is a delegate and what does the compiler generate for one?","A delegate is a type-safe reference to a method. For each delegate type the compiler generates a sealed class deriving from MulticastDelegate with an Invoke method matching the signature (plus BeginInvoke/EndInvoke, which aren't supported on .NET Core). Instances store Target and Method, and can hold several methods in an invocation list."),
("Basic","When would you declare your own delegate type instead of using Func/Action?","When a name documents intent better (e.g. <code>PriceRule</code>), when you need ref/out/in parameters or params (Func/Action can't express them), or for events following a convention. Otherwise Func/Action are preferred for consistency."),
("Basic","What is method group conversion?","Using a method name without parentheses where a delegate is expected. The compiler picks the overload matching the delegate's signature and creates the delegate, e.g. <code>Array.ConvertAll(strings, int.Parse)</code>."),
("Intermediate","Explain covariance and contravariance for delegates.","Covariance (<code>out</code>) lets a delegate returning a more derived type be used where a less derived return is expected: <code>Func&lt;UpiPayment&gt;</code> as <code>Func&lt;Payment&gt;</code>. Contravariance (<code>in</code>) lets a delegate accepting a base type be used where a derived parameter is passed: <code>Action&lt;Payment&gt;</code> as <code>Action&lt;UpiPayment&gt;</code>. It only applies to reference types, and only for type parameters marked in/out."),
("Intermediate","Delegate or interface for a strategy — how do you decide?","Use a delegate for small, stateless, single-method behaviour chosen at runtime (pricing rules, sort keys). Use an interface when the behaviour has several related methods, needs dependencies through DI, should be named and discoverable, or is mocked in tests as a unit."),
("Intermediate","What is a higher-order function? Give a real example.","A function that takes and/or returns functions. Examples: LINQ's Where (takes a predicate), a Retry helper that takes the operation plus an onRetry callback, or Memoize that takes a function and returns a caching version of it.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Lambdas, closures, local functions and extension methods",
"Write lambdas in all their forms, understand exactly what a closure captures (and the classic loop bug), choose between lambdas and local functions, and add your own extension methods and fluent APIs.",
[("Lambda expression","An anonymous function written inline: <code>(a, b) =&gt; a + b</code>. Converts to a delegate or an expression tree."),
("Expression lambda","A lambda whose body is a single expression: <code>o =&gt; o.Amount &gt; 1000</code>."),
("Statement lambda","A lambda with a block body <code>{ … }</code> and explicit <code>return</code>."),
("Natural type","Since C# 10, a lambda whose parameter types are known (explicitly typed, or no parameters) has a default delegate type, so <code>var</code> works."),
("Closure","A lambda (or local function) together with the outer variables it uses."),
("Captured variable","An outer local or parameter used inside a lambda. The lambda captures the <b>variable</b>, not a copy of its value."),
("Display class","The hidden class the compiler generates to hold captured variables as fields."),
("Loop-closure gotcha","All lambdas created in a <code>for</code> loop share the one loop variable, so they see its final value."),
("Static lambda","C# 9 <code>static x =&gt; …</code>: a lambda that is forbidden from capturing locals or <code>this</code>."),
("Discard parameters","C# 9 <code>(_, _) =&gt; 0</code>: parameters you don't use."),
("Local function","A named method declared inside another method; can be generic, recursive and <code>static</code>."),
("Extension method","A static method whose first parameter has <code>this</code>, callable as if it were an instance method."),
("Fluent API","An API whose methods return an object you can keep calling on: <code>builder.A().B().C()</code>."),
("Lambda default parameters","C# 12: <code>(decimal amt, decimal rate = 0.18m) =&gt; …</code>")],
["Closures capture variables, not values: later changes are visible to the lambda.",
"<code>for</code> shares one loop variable across iterations; <code>foreach</code> (since C# 5) gives a fresh one each time.",
"Mark lambdas <code>static</code> when they shouldn't capture: it documents intent and avoids hidden allocations.",
"Prefer local functions for named helpers inside a method; use lambdas when you need a delegate value.",
"Extension methods need their namespace imported, and a real instance method with the same signature always wins.",
"Every LINQ operator is an extension method on <code>IEnumerable&lt;T&gt;</code> — tomorrow will feel familiar."],
f'''
<h3>1. Lambda syntax, all forms</h3>
{C(r"""
Func<decimal, decimal> gst = p => p * 1.18m;                       // expression lambda, inferred type
Func<int, int, int> add = (a, b) => a + b;                          // two parameters need parentheses
Func<DateOnly> today = () => DateOnly.FromDateTime(DateTime.Today); // no parameters
Func<string, bool> isPin = (string s) => s.Length == 6;             // explicit parameter type

Func<decimal, string> slab = income =>                              // statement lambda
{
    if (income <= 300_000m) return "Nil";
    if (income <= 700_000m) return "5%";
    return "Higher slab";
};

Func<int, int, int> first = (a, _) => a;                            // discard (C# 9)

// C# 10: natural types and explicit return types
var greet = (string name) => $"Namaste, {name}";                    // Func<string, string>
var pick = object (bool b) => b ? 1 : "one";                        // explicit return type

// C# 12: default parameter values
var withGst = (decimal amount, decimal rate = 0.18m) => amount * (1 + rate);
Console.WriteLine(withGst(1000m));          // 1180.00
Console.WriteLine(withGst(1000m, 0.05m));   // 1050.00
""")}
<p><code>withGst</code> has a default parameter, which <code>Func</code> can't express, so its natural type is a compiler-generated delegate type rather than <code>Func&lt;decimal, decimal, decimal&gt;</code>.</p>

<h3>2. Closures: capturing variables</h3>
{C(r"""
decimal rate = 0.18m;
Func<decimal, decimal> tax = amount => amount * rate;   // captures the variable `rate`
Console.WriteLine(tax(100m));   // 18.00
rate = 0.05m;
Console.WriteLine(tax(100m));   // 5.00 — the lambda sees the new value

// A captured variable outlives the method that declared it
Func<string> MakeTokenGenerator(string prefix)
{
    int next = 0;                                // lives on inside the closure
    return () => $"{prefix}-{++next:D4}";
}

var counterA = MakeTokenGenerator("A");
var counterB = MakeTokenGenerator("B");
Console.WriteLine(counterA());   // A-0001
Console.WriteLine(counterA());   // A-0002
Console.WriteLine(counterB());   // B-0001 — each call to MakeTokenGenerator gets its own `next`
""", "Closures.cs")}
<p>What the compiler does, roughly: it moves captured locals into fields of a hidden class and turns the lambda into a method on that class.</p>
{C(r"""
// Simplified view of the generated code for MakeTokenGenerator
private sealed class DisplayClass
{
    public string prefix = "";
    public int next;
    public string Lambda() => $"{prefix}-{++next:D4}";
}
// MakeTokenGenerator now does: var d = new DisplayClass { prefix = prefix }; return d.Lambda;
""")}
<p>Two consequences: (1) a capturing lambda costs an allocation for the display class plus the delegate; (2) everything captured stays alive as long as the delegate does.</p>

<h3>3. The loop-closure gotcha</h3>
{C(r"""
var printers = new List<Action>();
for (int i = 0; i < 3; i++)
    printers.Add(() => Console.Write($"{i} "));
printers.ForEach(p => p());              // 3 3 3  — ONE shared i, read when the lambda runs

printers.Clear();
for (int i = 0; i < 3; i++)
{
    int copy = i;                        // a new variable per iteration
    printers.Add(() => Console.Write($"{copy} "));
}
printers.ForEach(p => p());              // 0 1 2

printers.Clear();
foreach (int n in new[] { 0, 1, 2 })     // C# 5+: foreach variable is fresh each iteration
    printers.Add(() => Console.Write($"{n} "));
printers.ForEach(p => p());              // 0 1 2
""", "LoopClosure.cs")}
{warn("The same bug appears with <code>Task.Run(() =&gt; Send(invoices[i]))</code> inside a <code>for</code> loop: tasks start later, by which time <code>i</code> may equal <code>invoices.Length</code> → IndexOutOfRangeException. Copy to a local or use foreach.", "Real-world")}

<h3>4. Static lambdas and avoiding hidden captures</h3>
{C(r"""
const decimal GstRate = 0.18m;
decimal festiveDiscount = 0.10m;

Func<decimal, decimal> a = static p => p * (1 + GstRate);          // ✓ constants are fine
// Func<decimal, decimal> b = static p => p * (1 - festiveDiscount); // ❌ CS8820: can't capture 'festiveDiscount'

// Pass the state in instead of capturing it
Func<decimal, decimal, decimal> c = static (p, discount) => p * (1 - discount);
Console.WriteLine(c(1000m, festiveDiscount));   // 900.00
""")}
<p>A non-capturing lambda is created once and cached by the compiler; a capturing one allocates every time the enclosing code runs. <code>static</code> turns accidental captures (including a hidden <code>this</code>) into compile errors — useful in hot paths and in library code.</p>

<h3>5. Local functions vs lambdas</h3>
{C(r"""
static decimal InvoiceTotal(IReadOnlyList<(string Item, int Qty, decimal Rate)> lines, bool isExport)
{
    ArgumentOutOfRangeException.ThrowIfZero(lines.Count);
    decimal subtotal = 0;
    foreach (var line in lines) subtotal += LineTotal(line.Qty, line.Rate);
    return subtotal + Tax(subtotal);

    // Declared after use — fine for local functions
    static decimal LineTotal(int qty, decimal rate) => qty * rate;      // static: captures nothing
    decimal Tax(decimal amount) => isExport ? 0m : amount * 0.18m;      // captures isExport
}

Console.WriteLine(InvoiceTotal([("Seeds", 10, 120m), ("Tray", 4, 350m)], isExport: false));   // 3068.00

// Recursion: natural with a local function, awkward with a lambda
static long Factorial(int n) => n <= 1 ? 1 : n * Factorial(n - 1);
Func<int, long> fact = null!;
fact = n => n <= 1 ? 1 : n * fact(n - 1);      // must declare, then assign, so it can refer to itself

// Generic local function — lambdas can't have their own type parameters
static T Clamp<T>(T value, T min, T max) where T : IComparable<T> =>
    value.CompareTo(min) < 0 ? min : value.CompareTo(max) > 0 ? max : value;
Console.WriteLine(Clamp(140, 0, 100));          // 100
""", "LocalFunctions.cs")}
{table(["","Local function","Lambda"],[
["Has a name / can be called before its declaration","Yes","No"],
["Generic type parameters","Yes","No"],
["Recursion","Natural","Needs declare-then-assign"],
["ref/out/params, <code>yield return</code>","Yes","No yield; ref/out need a custom delegate type"],
["Allocation when only called directly","None (captures go in a struct)","Delegate (+ closure if capturing)"],
["Is a value you can pass/store","Only after conversion to a delegate","Yes"],
["Use for","Helpers inside one method, iterators, validation","Arguments to LINQ, callbacks, strategies"]])}

<h3>6. Writing extension methods</h3>
<p>Rules: the method is <code>static</code>, in a non-generic, non-nested <code>static</code> class, and its first parameter has the <code>this</code> modifier. Callers must import the namespace. If the type already has an applicable instance method with that name, the instance method wins.</p>
{C(r"""
using System.Globalization;

namespace Toolkit.Extensions;

public static class StringExtensions
{
    private static readonly CultureInfo India = CultureInfo.GetCultureInfo("en-IN");

    // Indian PIN code: 6 digits, can't start with 0
    public static bool IsValidPinCode(this string? value) =>
        value is { Length: 6 } && value[0] != '0' && value.All(char.IsAsciiDigit);   // char.IsAsciiDigit: .NET 7+

    public static string ToTitleCase(this string value) =>
        India.TextInfo.ToTitleCase(value.ToLower(India));

    public static string Truncate(this string value, int max) =>
        value.Length <= max ? value : value[..(max - 1)] + "…";
}

public static class MoneyExtensions
{
    private static readonly CultureInfo India = CultureInfo.GetCultureInfo("en-IN");

    public static string ToRupees(this decimal amount) => amount.ToString("C", India);   // lakh/crore grouping
    public static decimal WithGst(this decimal amount, decimal rate = 0.18m) => Math.Round(amount * (1 + rate), 2);
}

public static class EnumerableExtensions
{
    // Apply a filter only when a condition holds — handy for optional search fields
    public static IEnumerable<T> WhereIf<T>(this IEnumerable<T> source, bool condition, Func<T, bool> predicate) =>
        condition ? source.Where(predicate) : source;
}
""", "Toolkit/Extensions/Extensions.cs")}
{C(r"""
using Toolkit.Extensions;

Console.WriteLine("411001".IsValidPinCode());     // True
Console.WriteLine("011001".IsValidPinCode());     // False
Console.WriteLine("rAHUL sHARMA".ToTitleCase());  // Rahul Sharma
Console.WriteLine(1234567.5m.ToRupees());         // ₹12,34,567.50
Console.WriteLine(1000m.WithGst());               // 1180.00

string? missing = null;
Console.WriteLine(missing.IsValidPinCode());      // False — no NullReferenceException: it's really
                                                  // StringExtensions.IsValidPinCode(missing)

// orders: List<Order> from Wednesday's SampleData
string? city = "Pune";
bool onlyPaid = true;
var results = orders
    .WhereIf(onlyPaid, o => o.Status == "Paid")
    .WhereIf(city is not null, o => o.City == city);
""", "Program.cs")}
{tip("C# 14 (.NET 10) adds <b>extension members</b>: an <code>extension(...)</code> block inside a static class that can declare extension <i>properties</i> and static members, not just methods. Classic <code>this</code>-parameter extension methods keep working and are what you'll see in most codebases.")}

<h3>7. Fluent APIs</h3>
<p>A fluent API returns an object from every call so calls chain. Builders return <code>this</code>; LINQ returns a new <code>IEnumerable&lt;T&gt;</code> each time. You'll meet fluent APIs everywhere: <code>WebApplication.CreateBuilder</code>, EF Core's model builder, FluentValidation.</p>
{C(r"""
public sealed record Invoice(string Customer, string? Gstin, decimal Subtotal, decimal Gst, decimal Total);

public sealed class InvoiceBuilder
{
    private readonly List<(string Item, int Qty, decimal Rate)> _lines = [];
    private string _customer = "";
    private string? _gstin;
    private decimal _gstRate = 0.18m;

    public InvoiceBuilder For(string customer) { _customer = customer; return this; }
    public InvoiceBuilder WithGstin(string gstin) { _gstin = gstin; return this; }
    public InvoiceBuilder GstRate(decimal rate) { _gstRate = rate; return this; }
    public InvoiceBuilder AddLine(string item, int qty, decimal rate)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(qty);
        _lines.Add((item, qty, rate));
        return this;
    }

    public Invoice Build()
    {
        if (string.IsNullOrWhiteSpace(_customer)) throw new InvalidOperationException("Customer is required");
        if (_lines.Count == 0) throw new InvalidOperationException("Add at least one line");
        decimal subtotal = _lines.Sum(l => l.Qty * l.Rate);
        decimal gst = Math.Round(subtotal * _gstRate, 2);
        return new Invoice(_customer, _gstin, subtotal, gst, subtotal + gst);
    }
}
""", "InvoiceBuilder.cs")}
{C(r"""
var invoice = new InvoiceBuilder()
    .For("Sharma Traders")
    .WithGstin("27ABCDE1234F1Z5")
    .AddLine("Drip irrigation kit", 2, 4_500m)
    .AddLine("Installation", 1, 1_200m)
    .Build();

Console.WriteLine($"{invoice.Customer}: {invoice.Subtotal.ToRupees()} + GST {invoice.Gst.ToRupees()} = {invoice.Total.ToRupees()}");
// Sharma Traders: ₹10,200.00 + GST ₹1,836.00 = ₹12,036.00
""")}
''',
["Creating lambdas in a <code>for</code> loop that use the loop variable.",
"Assuming a closure copies the value at creation time.",
"Capturing a large object (or <code>this</code>) in a long-lived lambda and keeping it alive.",
"Writing an extension method with the same name as an instance method and wondering why it's never called.",
"Putting extension methods in a namespace callers don't import, so they \"disappear\"."],
("40 min", ["Write <code>Func&lt;decimal&gt; MakeEmiCalculator(decimal principal, decimal annualRate, int months)</code> that returns a closure computing the EMI, then change the captured rate and observe the effect.",
"Reproduce the loop-closure bug with <code>Task.Run</code> and a <code>for</code> loop over 5 invoice numbers; fix it two ways.",
"Add extension methods <code>IsValidGstin()</code>, <code>MaskMobile()</code> (<code>98XXXXXX21</code>) and <code>ToIndianWords()</code> for numbers up to 99,99,999 to your Toolkit project."]),
[("What does a closure capture: the value or the variable?","The variable. The lambda reads the current value whenever it runs, and writes from inside the lambda are visible outside."),
("Why does a <code>for</code> loop print 3 3 3 but <code>foreach</code> print 0 1 2?","A for loop declares its variable once and mutates it, so all lambdas share it. Since C# 5, foreach declares a fresh iteration variable each time."),
("How is an extension method call compiled?","As an ordinary static call: <code>value.IsValidPinCode()</code> becomes <code>StringExtensions.IsValidPinCode(value)</code>. That's why it works on null.")],
[("Basic","What is a lambda expression?","An anonymous function written inline with <code>=&gt;</code>. It converts to a compatible delegate type (Func, Action, custom) or to an expression tree (<code>Expression&lt;Func&lt;…&gt;&gt;</code>) that libraries like EF Core can inspect."),
("Basic","What is a closure and what does it cost?","A lambda plus the outer variables it captures. The compiler hoists captured variables into a generated class; creating the lambda allocates that object and the delegate, and captured objects live as long as the delegate."),
("Basic","How do you write an extension method?","A static method in a non-generic, non-nested static class, whose first parameter is prefixed with <code>this</code>. Callers import the namespace and call it like an instance method."),
("Intermediate","Explain the loop-closure problem and its fixes.","Lambdas created inside a for loop capture the single loop variable, so when they run later they all see its final value. Fix by copying to a local inside the loop body, using foreach (fresh variable per iteration since C# 5), or passing the value as a parameter."),
("Intermediate","Local function or lambda — when do you use which?","Local functions for named helpers inside a method: they can be generic, recursive, use ref/out/yield, be declared after use and avoid delegate allocations. Lambdas when you need a delegate value — passing to LINQ, storing a callback, returning a function."),
("Intermediate","What is a static lambda and why use one?","A lambda marked <code>static</code> (C# 9) that may not capture locals or <code>this</code>. It guarantees no closure allocation and prevents accidental captures that keep objects alive; state must be passed as parameters.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "LINQ fundamentals: filter, project, sort, pick, partition",
"Use the everyday LINQ operators confidently, know which ones throw on empty input, and understand exactly when a query runs.",
[("LINQ","Language Integrated Query: a set of extension methods (in <code>System.Linq</code>) that query any <code>IEnumerable&lt;T&gt;</code>."),
("Sequence","Any <code>IEnumerable&lt;T&gt;</code>: arrays, lists, dictionaries, iterator methods, query results."),
("Query operator","A LINQ method such as Where, Select or OrderBy."),
("Filtering","Keeping elements that match a predicate: <code>Where</code>."),
("Projection","Transforming each element into something else: <code>Select</code>."),
("Anonymous type","A compiler-generated, read-only type created with <code>new { o.Id, o.Amount }</code>; great for projections inside one method."),
("Element operator","Returns one element: First, FirstOrDefault, Single, SingleOrDefault, Last, ElementAt."),
("Quantifier","Returns bool about the sequence: Any, All, Contains."),
("Partitioning","Taking a slice: Take, Skip, TakeWhile, SkipWhile, TakeLast, Chunk."),
("Deferred execution","The query is only a recipe; it runs when you enumerate it (foreach, ToList, Count…)."),
("Immediate execution","Operators that enumerate straight away and return a value or a collection: ToList, ToArray, Count, First, Sum, Max…"),
("Streaming vs buffering","Where/Select yield one item at a time; OrderBy and GroupBy must read the whole input before yielding the first item."),
("DistinctBy / MinBy / MaxBy",".NET 6 operators that compare or select by a key while returning the whole element."),
("Chunk",".NET 6: splits a sequence into arrays of a given size — perfect for batching.")],
["LINQ never changes the source collection; it produces new sequences.",
"First throws on no match; FirstOrDefault returns default (null for classes, 0 for numbers).",
"Single throws if there are zero <i>or more than one</i> matches — use it to assert uniqueness.",
"Use <code>ThenBy</code> for secondary sorts; a second <code>OrderBy</code> replaces the first.",
"<code>Any()</code> stops at the first match; <code>Count() &gt; 0</code> may walk everything.",
"A query is re-run every time you enumerate it; call ToList() once if you need the results more than once."],
f'''
<h3>1. Sample data, Where and Select</h3>
<p>All of this week's examples use the same small order list. Put it in a file and reuse it.</p>
{C(r"""
public record Order(int Id, string Customer, string City, decimal Amount, DateOnly Date, string Status);

public static class SampleData
{
    public static List<Order> Orders() =>
    [
        new(1001, "Asha",  "Pune",      2_499m,  new(2026, 10, 2),  "Delivered"),
        new(1002, "Ravi",  "Bengaluru", 899m,    new(2026, 10, 3),  "Cancelled"),
        new(1003, "Meena", "Chennai",   15_750m, new(2026, 10, 3),  "Delivered"),
        new(1004, "Imran", "Pune",      4_200m,  new(2026, 10, 5),  "Shipped"),
        new(1005, "Asha",  "Pune",      12_000m, new(2026, 10, 7),  "Delivered"),
        new(1006, "Kiran", "Hyderabad", 650m,    new(2026, 10, 8),  "Placed"),
        new(1007, "Ravi",  "Bengaluru", 7_300m,  new(2026, 10, 9),  "Delivered"),
        new(1008, "Neha",  "Jaipur",    3_150m,  new(2026, 10, 11), "Shipped"),
    ];
}
""", "SampleData.cs")}
{C(r"""
var orders = SampleData.Orders();

// Where = filter, Select = transform
IEnumerable<string> bigPune = orders
    .Where(o => o.City == "Pune" && o.Amount > 3_000m)
    .Select(o => $"#{o.Id} {o.Customer} {o.Amount:N0}");
Console.WriteLine(string.Join(" | ", bigPune));     // #1004 Imran 4,200 | #1005 Asha 12,000

// Index overloads
var numbered = orders.Select((o, i) => $"{i + 1}. {o.Customer}");          // 1. Asha, 2. Ravi, …
var everyOther = orders.Where((o, i) => i % 2 == 0);                       // 1001, 1003, 1005, 1007

// Projecting to an anonymous type or a tuple
var withGst = orders.Select(o => new { o.Id, o.Customer, Gross = o.Amount * 1.18m });
foreach (var x in withGst.Take(2)) Console.WriteLine(x);
// { Id = 1001, Customer = Asha, Gross = 2948.82 }
// { Id = 1002, Customer = Ravi, Gross = 1060.82 }

var pairs = orders.Select(o => (o.Id, Total: o.Amount));                    // (int Id, decimal Total)

// OfType filters AND casts — handy with mixed hierarchies (Week 2 library items)
object[] mixed = [1, "two", 3, 4.0];
IEnumerable<int> ints = mixed.OfType<int>();                                // 1, 3
""", "WhereSelect.cs")}
{tip("Anonymous types can't leave the method (you can't name them as a return type). If a projection needs to be returned, define a small <code>record</code>.")}

<h3>2. Sorting: OrderBy, ThenBy, Descending</h3>
{C(r"""
var sorted = orders
    .OrderBy(o => o.City)                 // primary key
    .ThenByDescending(o => o.Amount);     // tie-breaker within each city

foreach (var o in sorted) Console.WriteLine($"{o.City,-10} {o.Amount,8:N0}");
// Bengaluru     7,300
// Bengaluru       899
// Chennai      15,750
// Hyderabad       650
// Jaipur        3,150
// Pune         12,000
// Pune          4,200
// Pune          2,499

// ❌ Second OrderBy REPLACES the first ordering (it becomes the primary key)
var wrong = orders.OrderBy(o => o.City).OrderByDescending(o => o.Amount);

// Custom comparer and .NET 7 Order()/OrderDescending() for simple values
var names = orders.Select(o => o.Customer).Distinct().Order(StringComparer.OrdinalIgnoreCase);
var amounts = orders.Select(o => o.Amount).OrderDescending();
""", "Sorting.cs")}
<p>LINQ's OrderBy is a <b>stable</b> sort: items with equal keys keep their original relative order. <code>List&lt;T&gt;.Sort</code> is not stable.</p>

<h3>3. Picking one element</h3>
{C(r"""
Order firstShipped = orders.First(o => o.Status == "Shipped");           // #1004
Order? delhi = orders.FirstOrDefault(o => o.City == "Delhi");            // null
Order lastDelivered = orders.Last(o => o.Status == "Delivered");         // #1007
Order byId = orders.Single(o => o.Id == 1003);                           // exactly one → Meena
Order? zoya = orders.SingleOrDefault(o => o.Customer == "Zoya");         // none → null

// orders.First(o => o.City == "Delhi");          // ❌ InvalidOperationException: no matching element
// orders.Single(o => o.Customer == "Asha");      // ❌ InvalidOperationException: more than one matching element
// orders.SingleOrDefault(o => o.Customer == "Asha"); // ❌ still throws: "OrDefault" only covers zero matches

// Value types: default is 0, which may be a real value — use the .NET 6 overload with your own default
decimal huge = orders.Select(o => o.Amount).FirstOrDefault(a => a > 50_000m, -1m);   // -1
""", "ElementOperators.cs")}
{table(["Operator","No match","One match","Several matches"],[
["<code>First</code>","throws","returns it","returns the first"],
["<code>FirstOrDefault</code>","default / your fallback","returns it","returns the first"],
["<code>Single</code>","throws","returns it","throws"],
["<code>SingleOrDefault</code>","default","returns it","throws"],
["<code>Last</code> / <code>LastOrDefault</code>","throws / default","returns it","returns the last"],
["<code>ElementAt(i)</code> / <code>ElementAtOrDefault</code>","throws / default if out of range","",""]])}
{tip("Use <code>Single</code> when duplicates would be a bug (lookup by primary key) — it fails loudly. Use <code>First</code> when any match will do.")}

<h3>4. Quantifiers, counting and partitioning</h3>
{C(r"""
bool anyCancelled = orders.Any(o => o.Status == "Cancelled");   // True — stops at the first hit
bool allPositive  = orders.All(o => o.Amount > 0);              // True
int delivered     = orders.Count(o => o.Status == "Delivered"); // 4
bool hasOrders    = orders.Any();                               // prefer over Count() > 0
bool vacuous      = new List<Order>().All(o => o.Amount > 1_000_000m);   // True! All on empty is true

// .NET 6: count without enumerating, if the source knows its size
if (orders.TryGetNonEnumeratedCount(out int n)) Console.WriteLine(n);   // 8

// Partitioning
var top3 = orders.OrderByDescending(o => o.Amount).Take(3);             // 1003, 1005, 1007
var lastTwo = orders.Take(^2..);                                        // .NET 6 range: 1007, 1008
var earlyOctober = orders.OrderBy(o => o.Date)
                         .TakeWhile(o => o.Date < new DateOnly(2026, 10, 5));   // 1001, 1002, 1003

// Paging (you'll use this exact formula in Web APIs)
int page = 2, pageSize = 3;
var page2 = orders.OrderBy(o => o.Id).Skip((page - 1) * pageSize).Take(pageSize);   // 1004, 1005, 1006

// Chunk (.NET 6): batches for bulk SMS, API calls, DB inserts
foreach (Order[] batch in orders.Chunk(3))
    Console.WriteLine($"Batch: {string.Join(",", batch.Select(o => o.Id))}");
// Batch: 1001,1002,1003
// Batch: 1004,1005,1006
// Batch: 1007,1008
""", "QuantifiersPartitioning.cs")}
{warn("TakeWhile stops at the first element that fails the condition, even if later ones would pass. It's not a filter; that's Where.", "Gotcha")}

<h3>5. Distinct, DistinctBy, Min/Max, MinBy/MaxBy</h3>
{C(r"""
var cities = orders.Select(o => o.City).Distinct();
// Pune, Bengaluru, Chennai, Hyderabad, Jaipur

var firstOrderPerCustomer = orders.DistinctBy(o => o.Customer);         // .NET 6: whole Order, first per key
// 1001 Asha, 1002 Ravi, 1003 Meena, 1004 Imran, 1006 Kiran, 1008 Neha

var uniqueCities = orders.Select(o => o.City).Distinct(StringComparer.OrdinalIgnoreCase);

decimal maxAmount = orders.Max(o => o.Amount);         // 15750 — just the value
Order biggest  = orders.MaxBy(o => o.Amount)!;         // .NET 6: the whole order → #1003 Meena
Order smallest = orders.MinBy(o => o.Amount)!;         // #1006 Kiran (650)

// Before .NET 6 people wrote this — reads as a full sort (O(n log n) on .NET Framework;
// .NET Core optimises OrderBy(...).First() to one linear pass, but MaxBy states the intent):
Order biggestOld = orders.OrderByDescending(o => o.Amount).First();
""", "DistinctMinMax.cs")}
<p>Distinct uses <code>Equals</code>/<code>GetHashCode</code>, so it works on records by value (Week 3) and on classes only by reference unless you pass an <code>IEqualityComparer&lt;T&gt;</code> (Week 4). MinBy/MaxBy return the first element with the extreme key when there are ties.</p>

<h3>6. Deferred vs immediate execution</h3>
<p>Most operators return an object describing the query. Nothing runs until something enumerates it. This is the <code>yield return</code> behaviour you saw last Thursday.</p>
{C(r"""
var numbers = new List<int> { 1, 2, 3 };

var evens = numbers.Where(n =>
{
    Console.Write($"[check {n}]");
    return n % 2 == 0;
});
Console.WriteLine("query built");     // nothing checked yet
numbers.Add(4);                       // the query will see this!

foreach (var e in evens) Console.Write($" →{e} ");
// query built
// [check 1][check 2] →2 [check 3][check 4] →4

// Enumerating twice runs the predicate twice
int count = evens.Count();            // checks 1,2,3,4 again
var cached = evens.ToList();          // run once, store results; later reads are free
""", "Deferred.cs")}
{table(["Deferred (returns a query)","Immediate (runs now)"],[
["Where, Select, SelectMany, OfType, Cast","ToList, ToArray, ToDictionary, ToHashSet, ToLookup"],
["OrderBy, ThenBy, Reverse, GroupBy, Join","Count, LongCount, Any, All, Contains"],
["Take, Skip, TakeWhile, Chunk, Distinct, Zip","First, Single, Last, ElementAt (+ OrDefault)"],
["Concat, Union, Intersect, Except","Sum, Average, Min, Max, MinBy, MaxBy, Aggregate"]])}
<p class="muted">OrderBy and GroupBy are deferred, but when they <i>do</i> run they read the whole source before yielding anything (buffering). Where and Select stream one item at a time.</p>
{warn("Deferred execution plus a closure is a classic bug: build <code>var q = orders.Where(o =&gt; o.City == city);</code>, change <code>city</code>, then enumerate — you get the new city's orders. Materialise with ToList() when you want a snapshot.", "Gotcha")}
''',
["Using <code>First</code> where no match is possible and getting \"Sequence contains no matching element\".",
"Chaining two <code>OrderBy</code> calls instead of <code>OrderBy</code> + <code>ThenBy</code>.",
"Calling <code>Count() &gt; 0</code> instead of <code>Any()</code>.",
"Enumerating the same expensive query several times (in a loop condition, then a foreach, then Count).",
"Expecting <code>FirstOrDefault</code> on an <code>int</code> sequence to return null."],
("40 min", ["Create 15 <code>Employee</code> records (Name, Department, City, Salary in ₹ LPA, JoinDate). Print: engineers in Bengaluru sorted by salary desc then name; the 3 most recent joiners; the highest-paid person per department using MaxBy inside a loop over distinct departments.",
"Page through the employees 4 at a time with Skip/Take, then do the same with Chunk. Print page headers.",
"Prove deferred execution: build a query, add an employee, then enumerate. Then fix it with ToList() and show the difference."]),
[("What is the difference between First and Single?","First returns the first match and ignores others. Single requires exactly one match and throws if there are none or more than one."),
("Which runs first in <code>q = list.Where(...); list.Add(x); q.ToList();</code>?","Nothing runs at the Where line. The predicate runs during ToList, after Add, so x is included if it matches."),
("Why is MaxBy better than OrderByDescending().First()?","MaxBy is guaranteed to be a single O(n) pass with no extra memory and says what you mean. A real sort is O(n log n) and buffers the whole sequence; modern .NET happens to optimise OrderBy(…).First() into a linear scan, but .NET Framework and many IQueryable providers don't, so don't rely on it.")],
[("Basic","What is LINQ?","Language Integrated Query: a set of extension methods (and query syntax) for querying sequences in a uniform way — in-memory objects via IEnumerable&lt;T&gt; (LINQ to Objects) and remote sources like databases via IQueryable&lt;T&gt; (EF Core)."),
("Basic","What is deferred execution?","Most LINQ operators return a query object instead of results. The query runs only when enumerated (foreach, ToList, Count, First…), and it runs again each time it's enumerated, seeing the current state of the source."),
("Basic","First vs FirstOrDefault vs Single vs SingleOrDefault?","First: first match, throws if none. FirstOrDefault: first match or default. Single: exactly one, throws on zero or many. SingleOrDefault: one or default, throws on many."),
("Intermediate","Why prefer Any() over Count() > 0?","Any() stops at the first element (or uses a known count); Count() on a non-collection must enumerate everything. On IQueryable, Any translates to EXISTS, which the database can stop early on."),
("Intermediate","OrderBy().OrderBy() vs OrderBy().ThenBy()?","The second OrderBy re-sorts the whole sequence by a new primary key (stability means the first key only survives as a tie-breaker by accident). ThenBy adds a secondary key to the existing ordering, which is the intent and what translates correctly to SQL."),
("Intermediate","Which LINQ operators buffer and why does it matter?","OrderBy, GroupBy, Reverse, Distinct (as it goes) and ToList/ToArray hold items in memory. On huge or infinite sequences, buffering operators consume memory and can't yield the first result until the input is fully read; Where/Select stream.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "LINQ: grouping, joins, flattening, aggregates and set operations",
"Summarise and combine data the way reports need: group and aggregate, inner and left joins, flatten nested lists, build lookups, and compare sets by key.",
[("GroupBy","Splits a sequence into groups by key; each group is an <code>IGrouping&lt;TKey, TElement&gt;</code>, which is a sequence with a <code>Key</code>."),
("Composite key","Grouping or joining on several values at once, using a tuple or anonymous type."),
("Join","Inner join: pairs elements of two sequences whose keys are equal. Unmatched items are dropped."),
("GroupJoin","For each outer element, gives the (possibly empty) group of matching inner elements."),
("Left join","Keep every outer element even with no match: GroupJoin + SelectMany + DefaultIfEmpty (or <code>LeftJoin</code> in .NET 10)."),
("SelectMany","Flattens a sequence of sequences into one sequence."),
("Zip","Pairs elements by position from two or three sequences; stops at the shortest."),
("Aggregate","General fold: combines all elements into one value with an accumulator function."),
("ToDictionary","Materialises key → element (or value). Throws on duplicate keys."),
("ToLookup","Materialises key → many elements. Immutable; a missing key gives an empty sequence."),
("Set operators","Union, Intersect, Except: treat sequences as sets (duplicates removed)."),
("*By set operators",".NET 6 UnionBy, IntersectBy, ExceptBy: compare elements by a key selector."),
("CountBy / AggregateBy",".NET 9 shortcuts for \"group and count\" / \"group and fold\" without building groups.")],
["GroupBy keeps groups in order of each key's first appearance, and items in original order inside a group.",
"Sum on an empty sequence is 0; Average, Min and Max on an empty non-nullable sequence throw.",
"Join builds a hash lookup of the inner sequence, so it's O(n + m), not nested loops.",
"ToDictionary throws on duplicate keys — group first or use ToLookup.",
"Concat keeps duplicates; Union removes them.",
"IntersectBy and ExceptBy take a sequence of <i>keys</i> as the second argument, not elements."],
f'''
<p>Extra data for today, alongside Wednesday's orders:</p>
{C(r"""
var customers = new List<Customer>
{
    new("Asha",  "Pune",      "Gold"),
    new("Ravi",  "Bengaluru", "Silver"),
    new("Meena", "Chennai",   "Gold"),
    new("Imran", "Pune",      "Silver"),
    new("Kiran", "Hyderabad", "Silver"),
    new("Neha",  "Jaipur",    "Gold"),
    new("Zoya",  "Lucknow",   "Silver"),   // no orders yet — watch her in the joins
};

public record Customer(string Name, string City, string Tier);
""", "Customers.cs")}

<h3>1. GroupBy</h3>
{C(r"""
var byCity = orders
    .GroupBy(o => o.City)
    .Select(g => new { City = g.Key, Orders = g.Count(), Total = g.Sum(o => o.Amount) })
    .OrderByDescending(x => x.Total);

foreach (var c in byCity) Console.WriteLine($"{c.City,-10} {c.Orders} orders  ₹{c.Total,8:N0}");
// Pune       3 orders  ₹  18,699
// Chennai    1 orders  ₹  15,750
// Bengaluru  2 orders  ₹   8,199
// Jaipur     1 orders  ₹   3,150
// Hyderabad  1 orders  ₹     650

// A group IS a sequence — you can loop over it
foreach (IGrouping<string, Order> g in orders.GroupBy(o => o.Status))
{
    Console.WriteLine($"{g.Key}: {string.Join(", ", g.Select(o => o.Id))}");
}
// Delivered: 1001, 1003, 1005, 1007
// Cancelled: 1002
// Shipped: 1004, 1008
// Placed: 1006

// Composite key with a tuple; element selector picks what goes in each group
var amountsByCityStatus = orders.GroupBy(
    keySelector: o => (o.City, o.Status),
    elementSelector: o => o.Amount);
foreach (var g in amountsByCityStatus.Where(g => g.Count() > 1))
    Console.WriteLine($"{g.Key.City}/{g.Key.Status}: {g.Sum():N0}");   // Pune/Delivered: 14,499

// .NET 9 shortcuts
foreach (var (city, count) in orders.CountBy(o => o.City))
    Console.Write($"{city}={count} ");                                 // Pune=3 Bengaluru=2 Chennai=1 …
var totals = orders.AggregateBy(o => o.City, seed: 0m, (sum, o) => sum + o.Amount);   // KeyValuePair<string, decimal>s
""", "GroupBy.cs")}

<h3>2. Join and left join</h3>
{C(r"""
// Inner join: orders ⋈ customers on name
var withTier = orders.Join(customers,
    o => o.Customer,              // outer key
    c => c.Name,                  // inner key
    (o, c) => new { o.Id, c.Name, c.Tier, o.Amount });

var tierTotals = withTier.GroupBy(x => x.Tier)
                         .Select(g => $"{g.Key}: ₹{g.Sum(x => x.Amount):N0}");
Console.WriteLine(string.Join(" | ", tierTotals));   // Gold: ₹33,399 | Silver: ₹13,049
// Zoya doesn't appear anywhere — she has no orders, and inner join drops her

// GroupJoin: every customer with their (possibly empty) orders
var summary = customers.GroupJoin(orders,
    c => c.Name,
    o => o.Customer,
    (c, theirOrders) => new { c.Name, Count = theirOrders.Count(), Total = theirOrders.Sum(o => o.Amount) });

foreach (var s in summary) Console.WriteLine($"{s.Name,-6} {s.Count}  ₹{s.Total:N0}");
// Asha   2  ₹14,499
// Ravi   2  ₹8,199
// Meena  1  ₹15,750
// Imran  1  ₹4,200
// Kiran  1  ₹650
// Neha   1  ₹3,150
// Zoya   0  ₹0          ← kept

// Flat left join: one row per order, plus one row for customers with none
var leftJoin = customers
    .GroupJoin(orders, c => c.Name, o => o.Customer, (c, os) => new { c, os })
    .SelectMany(x => x.os.DefaultIfEmpty(),                // empty group → a single null
                (x, o) => new { x.c.Name, OrderId = o?.Id, Amount = o?.Amount ?? 0m });

foreach (var r in leftJoin.Where(r => r.OrderId is null))
    Console.WriteLine($"{r.Name}: no orders");             // Zoya: no orders
""", "Joins.cs")}
{tip(".NET 10 adds <code>LeftJoin</code> and <code>RightJoin</code> operators, so <code>customers.LeftJoin(orders, c =&gt; c.Name, o =&gt; o.Customer, (c, o) =&gt; …)</code> replaces the GroupJoin/SelectMany/DefaultIfEmpty dance. Learn the classic pattern anyway: it's in every existing codebase and interview.")}

<h3>3. SelectMany and Zip</h3>
{C(r"""
var invoices = new List<Invoice>
{
    new("INV-101", "Asha", [new("Pen", 3, 20m), new("Notebook", 2, 60m)]),
    new("INV-102", "Ravi", [new("Pen", 5, 20m)]),
    new("INV-103", "Neha", [new("Stapler", 1, 150m), new("Notebook", 4, 60m)]),
};

// Select gives a sequence of lists; SelectMany flattens to one sequence of lines
IEnumerable<List<Line>> nested = invoices.Select(i => i.Lines);       // 3 lists
IEnumerable<Line> flat = invoices.SelectMany(i => i.Lines);           // 5 lines

var unitsPerItem = flat.GroupBy(l => l.Item)
                       .Select(g => $"{g.Key}={g.Sum(l => l.Qty)}");
Console.WriteLine(string.Join(", ", unitsPerItem));   // Pen=8, Notebook=6, Stapler=1

// Result selector keeps access to the parent
var rows = invoices.SelectMany(i => i.Lines, (inv, line) => $"{inv.No} {line.Item} x{line.Qty}");
// INV-101 Pen x3, INV-101 Notebook x2, INV-102 Pen x5, …

// Zip: pair by position
string[] months = ["Jul", "Aug", "Sep"];
decimal[] sales  = [1.2m, 1.5m, 1.1m];     // ₹ lakh
decimal[] target = [1.0m, 1.6m, 1.0m];

foreach (var (m, s, t) in months.Zip(sales, target))      // 3-way Zip returns tuples (.NET 6)
    Console.WriteLine($"{m}: {s} vs {t} → {(s >= t ? "hit" : "miss")}");
// Jul: 1.2 vs 1.0 → hit
// Aug: 1.5 vs 1.6 → miss
// Sep: 1.1 vs 1.0 → hit

// Month-over-month change: zip a sequence with itself shifted by one
var change = sales.Zip(sales.Skip(1), (prev, curr) => curr - prev);   // 0.3, -0.4

public record Line(string Item, int Qty, decimal Rate);
public record Invoice(string No, string Customer, List<Line> Lines);
""", "SelectManyZip.cs")}

<h3>4. Aggregates</h3>
{C(r"""
decimal total   = orders.Sum(o => o.Amount);          // 46448
decimal average = orders.Average(o => o.Amount);      // 5806
decimal min     = orders.Min(o => o.Amount);          // 650
int count       = orders.Count;                       // 8 — List property, not the LINQ method

// Aggregate = general fold. Compound interest: ₹1 lakh FD at 7% for 3 years
decimal maturity = Enumerable.Range(1, 3).Aggregate(100_000m, (balance, _) => balance * 1.07m);
Console.WriteLine($"{maturity:N2}");                  // 1,22,504.30 in en-IN · 122,504.30 in en-US

// Aggregate with seed + result selector: longest customer name
string longest = customers.Aggregate("", (best, c) => c.Name.Length > best.Length ? c.Name : best,
                                     best => best.ToUpper());   // MEENA

// Empty sequences
int[] none = [];
Console.WriteLine(none.Sum());                        // 0
// none.Average();  none.Max();                       // ❌ InvalidOperationException: Sequence contains no elements
Console.WriteLine(none.Select(x => (int?)x).Max() is null);   // True — nullable versions return null
Console.WriteLine(none.DefaultIfEmpty().Average());   // 0 — or supply a default explicitly
""", "Aggregates.cs")}
{table(["On an empty sequence","Result"],[
["<code>Count</code>, <code>Sum</code>","0"],
["<code>Average</code>, <code>Min</code>, <code>Max</code> of non-nullable value types","throws InvalidOperationException"],
["<code>Min</code>/<code>Max</code>/<code>Average</code> of nullable or reference types","null"],
["<code>MinBy</code>/<code>MaxBy</code>","null for reference types, throws for value types"],
["<code>Aggregate</code> without seed","throws"],
["<code>Aggregate</code> with seed","the seed"],
["<code>All</code> / <code>Any</code>","true / false"]])}
{warn("<code>Sum</code> over <code>int</code> uses checked arithmetic and throws <code>OverflowException</code> instead of wrapping. Sum marks into a <code>long</code> or <code>decimal</code> when totals can be large.", "Note")}

<h3>5. ToDictionary, ToLookup, ToHashSet</h3>
{C(r"""
Dictionary<int, Order> byId = orders.ToDictionary(o => o.Id);
Console.WriteLine(byId[1005].Customer);                          // Asha — O(1) from now on

// orders.ToDictionary(o => o.Customer);   // ❌ ArgumentException: An item with the same key has already been added. Key: Asha

// One key → many values: ToLookup
ILookup<string, Order> byCustomer = orders.ToLookup(o => o.Customer);
Console.WriteLine(byCustomer["Asha"].Count());                   // 2
Console.WriteLine(byCustomer["Zoya"].Any());                     // False — missing key = empty, no exception

// Group then dictionary: key → aggregate
Dictionary<string, decimal> spendByCustomer = orders
    .GroupBy(o => o.Customer)
    .ToDictionary(g => g.Key, g => g.Sum(o => o.Amount), StringComparer.OrdinalIgnoreCase);

HashSet<string> orderCities = orders.Select(o => o.City).ToHashSet();
var notOrderedFrom = customers.Where(c => !orderCities.Contains(c.City));   // Zoya (Lucknow)
""", "Materialise.cs")}
{table(["","GroupBy","ToLookup","ToDictionary"],[
["Execution","Deferred (re-groups every enumeration)","Immediate","Immediate"],
["Values per key","Many","Many","One"],
["Missing key","n/a","Empty sequence","KeyNotFoundException"],
["Duplicate keys","Grouped","Grouped","Throws"],
["Mutable","n/a","No","Yes"]])}

<h3>6. Set operations and the *By variants</h3>
{C(r"""
string[] mondayBuyers  = ["Asha", "Ravi", "Meena"];
string[] tuesdayBuyers = ["Ravi", "Neha", "Asha", "Kiran"];

mondayBuyers.Union(tuesdayBuyers);       // Asha, Ravi, Meena, Neha, Kiran — distinct
mondayBuyers.Concat(tuesdayBuyers);      // all 7, duplicates kept
mondayBuyers.Intersect(tuesdayBuyers);   // Asha, Ravi — bought both days
mondayBuyers.Except(tuesdayBuyers);      // Meena — Monday only

// .NET 6: compare whole objects by a key
var catalog = new[]
{
    new Product("SKU-1", "Pen", 20m),
    new Product("SKU-2", "Notebook", 60m),
    new Product("SKU-3", "Stapler", 150m),
};
var incoming = new[]
{
    new Product("SKU-3", "Stapler", 145m),
    new Product("SKU-4", "Marker", 35m),
};

var merged = catalog.UnionBy(incoming, p => p.Sku);                 // SKU-1, 2, 3 (₹150 — first wins), 4
var active = catalog.ExceptBy(new[] { "SKU-2" }, p => p.Sku);       // second arg is KEYS: Pen, Stapler
var onSale = catalog.IntersectBy(new[] { "SKU-1", "SKU-3" }, p => p.Sku);   // Pen, Stapler
var brandNew = incoming.ExceptBy(catalog.Select(p => p.Sku), p => p.Sku);   // Marker

public record Product(string Sku, string Name, decimal Price);
""", "SetOperations.cs")}
''',
["Calling <code>ToDictionary</code> on a non-unique key (customer name, city) and crashing in production.",
"Calling <code>Average</code> or <code>Max</code> on a filtered sequence that can be empty.",
"Using Join when you need every outer row (that's a left join).",
"Using <code>Select</code> instead of <code>SelectMany</code> and getting a sequence of lists.",
"Passing elements instead of keys as the second argument of <code>ExceptBy</code>/<code>IntersectBy</code>."],
("40 min", ["Using the orders and customers: total spend per tier, the top customer per city (GroupBy + MaxBy), and every customer with their order count including zero (GroupJoin).",
"Model <code>Department(Name, List&lt;Employee&gt;)</code>; use SelectMany to find all employees earning above ₹15 LPA across departments, with the department name in the output.",
"Given yesterday's and today's stock lists of <code>Product</code>, print new SKUs, removed SKUs and SKUs whose price changed (Join on Sku where prices differ)."]),
[("What does GroupJoin return for an outer element with no matches?","The outer element paired with an empty sequence. That's what makes it the basis for left joins."),
("What happens with <code>new int[0].Average()</code>?","It throws InvalidOperationException (\"Sequence contains no elements\"). Sum would return 0."),
("When do you choose ToLookup over GroupBy?","When you'll look groups up by key repeatedly: ToLookup runs once and gives O(1) key access; GroupBy is deferred and re-groups each time it's enumerated.")],
[("Basic","What does GroupBy return?","A sequence of <code>IGrouping&lt;TKey, TElement&gt;</code>. Each grouping has a Key and is itself an IEnumerable of the elements with that key. It is deferred, and groups appear in order of first key appearance."),
("Basic","What is the difference between Select and SelectMany?","Select maps each element to exactly one result, so mapping to a collection gives a sequence of collections. SelectMany maps each element to a sequence and flattens the results into one sequence."),
("Basic","Union vs Concat?","Concat appends one sequence to another and keeps duplicates. Union returns the distinct elements of both, using the default (or supplied) equality comparer."),
("Intermediate","How do you write a left outer join in LINQ?","GroupJoin the outer to the inner sequence, then SelectMany over each group with DefaultIfEmpty() so an empty group yields one null, and handle the null in the result selector. In query syntax: <code>join … into g from x in g.DefaultIfEmpty()</code>. .NET 10 also offers a built-in LeftJoin."),
("Intermediate","ToDictionary vs ToLookup?","ToDictionary maps each key to one value, is mutable and throws on duplicate keys. ToLookup maps each key to a sequence, is immutable, allows duplicates and returns an empty sequence for missing keys."),
("Intermediate","How does LINQ's Join perform?","It builds a hash-based lookup of the inner sequence by key, then streams the outer sequence probing that lookup: about O(n + m), much better than nested loops' O(n × m). The inner sequence is fully buffered.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Query syntax, IEnumerable vs IQueryable, expression trees and LINQ performance",
"Read and write query syntax, know exactly how it maps to method calls, understand why EF Core needs IQueryable and expression trees, and avoid the common LINQ performance traps.",
[("Query syntax","SQL-like LINQ form: <code>from … where … select …</code>. The compiler translates it into method calls."),
("Method syntax","Calling the extension methods directly: <code>orders.Where(…).Select(…)</code>."),
("Range variable","The variable introduced by <code>from o in orders</code>; it refers to the current element."),
("let","Introduces a computed variable inside a query, usable in later clauses."),
("into","Continues a query after <code>group</code>, <code>select</code> or <code>join</code> under a new name."),
("Transparent identifier","Compiler-generated anonymous type carrying several range variables through a translated query (from let/multiple from)."),
("IQueryable&lt;T&gt;","A query against a provider (EF Core, OData). Holds an <code>Expression</code> and a <code>Provider</code> that translates and executes it."),
("Expression tree","Code represented as data: a tree of <code>Expression</code> nodes that can be inspected, translated (to SQL) or compiled."),
("Expression&lt;Func&lt;…&gt;&gt;","The type that makes the compiler build an expression tree from a lambda instead of a delegate."),
("Query provider","The component (e.g. EF Core) that turns an expression tree into something executable such as SQL."),
("AsEnumerable / AsQueryable","Switch a query between LINQ to Objects (in-memory) and provider-based execution."),
("Multiple enumeration","Running the same deferred query more than once, repeating its work (or its database round trip).")],
["Query and method syntax compile to the same thing; pick whichever reads better.",
"Query syntax shines with joins, <code>let</code> and multiple <code>from</code>; method syntax is needed for Take, Count, First, Distinct, MinBy…",
"<code>IEnumerable</code> methods take <code>Func</code> (code). <code>IQueryable</code> methods take <code>Expression&lt;Func&gt;</code> (data).",
"Passing a <code>Func</code> to an EF query silently switches to in-memory filtering after loading all rows.",
"Materialise once (ToList) when you'll enumerate more than once.",
"Measure before optimising: LINQ is fast enough for most code; avoid it only in proven hot paths."],
f'''
<h3>1. Query syntax basics and how it translates</h3>
{C(r"""
var delivered =
    from o in orders
    where o.Status == "Delivered"
    orderby o.Amount descending
    select new { o.Id, o.Customer, o.Amount };

// The compiler rewrites it to exactly this:
var delivered2 = orders
    .Where(o => o.Status == "Delivered")
    .OrderByDescending(o => o.Amount)
    .Select(o => new { o.Id, o.Customer, o.Amount });

foreach (var d in delivered) Console.WriteLine($"{d.Id} {d.Customer,-6} {d.Amount,8:N0}");
// 1003 Meena    15,750
// 1005 Asha     12,000
// 1007 Ravi      7,300
// 1001 Asha      2,499

// Multiple sort keys: comma-separated → OrderBy(...).ThenByDescending(...)
var byCity = from o in orders
             orderby o.City, o.Amount descending
             select o;
""", "QuerySyntax.cs")}
<p>Every query starts with <code>from</code> and ends with <code>select</code> or <code>group</code>. Query syntax is pattern-based: it works on any type that has suitably named methods (Where, Select…), which is how it works for both IEnumerable and IQueryable.</p>

<h3>2. let, group … into, join and multiple from</h3>
{C(r"""
// let: compute once, reuse
var gstHeavy =
    from o in orders
    let gst = o.Amount * 0.18m
    where gst > 1_000m
    select $"{o.Id}: GST {gst:N2}";
// 1003: GST 2,835.00 · 1005: GST 2,160.00 · 1007: GST 1,314.00

// group … by … into: continue querying the groups
var busyCities =
    from o in orders
    group o by o.City into g
    where g.Count() > 1
    orderby g.Key
    select new { City = g.Key, Orders = g.Count(), Total = g.Sum(o => o.Amount) };
// { City = Bengaluru, Orders = 2, Total = 8199 }, { City = Pune, Orders = 3, Total = 18699 }

// join … on … equals …: inner join (note: `equals`, not ==; outer key on the left)
var goldOrders =
    from o in orders
    join c in customers on o.Customer equals c.Name
    where c.Tier == "Gold"
    select new { o.Id, c.Name, o.Amount };

// join … into + DefaultIfEmpty: left join — far easier to read than method syntax
var everyone =
    from c in customers
    join o in orders on c.Name equals o.Customer into theirOrders
    from o in theirOrders.DefaultIfEmpty()
    select new { c.Name, OrderId = o?.Id, Amount = o?.Amount ?? 0m };

// Multiple from = SelectMany (cross join or flattening)
string[] sizes = ["S", "M", "L"];
string[] colours = ["Red", "Blue"];
var skus = from c in colours
           from s in sizes
           select $"{c}-{s}";                       // Red-S, Red-M, Red-L, Blue-S, Blue-M, Blue-L

// Composite join key: anonymous types with matching property names
// join s in stock on new { o.City, o.Sku } equals new { s.City, s.Sku }
""", "QueryClauses.cs")}
{table(["Query clause","Method call"],[
["<code>where x</code>","<code>.Where(…)</code>"],
["<code>select x</code>","<code>.Select(…)</code> (omitted when it just returns the range variable after another clause)"],
["<code>orderby a, b descending</code>","<code>.OrderBy(a).ThenByDescending(b)</code>"],
["<code>group x by k</code>","<code>.GroupBy(k, x)</code>"],
["<code>join … on … equals …</code>","<code>.Join(…)</code>"],
["<code>join … into g</code>","<code>.GroupJoin(…)</code>"],
["second <code>from</code>","<code>.SelectMany(…)</code>"],
["<code>let v = expr</code>","<code>.Select(x =&gt; new { x, v = expr })</code> (transparent identifier)"]])}
<p>There's no query keyword for Take, Skip, Distinct, Count, Sum, First, Any, MinBy, ToList, etc. Wrap the query in parentheses and continue in method syntax: <code>(from o in orders where … select o).Take(5).ToList()</code>.</p>

<h3>3. Which syntax should you use?</h3>
{table(["Situation","Prefer"],[
["Simple filter / project / sort chain","Method syntax (team norm in most .NET codebases)"],
["Joins, especially left joins","Query syntax"],
["Intermediate values reused across clauses","Query syntax with <code>let</code>"],
["Several nested <code>from</code> (flattening, cross joins)","Query syntax"],
["Paging, aggregates, element operators, .NET 6+ operators","Method syntax (no keywords exist)"]])}

<h3>4. Expression trees: Func vs Expression&lt;Func&gt;</h3>
<p>The same lambda can become two very different things depending on the target type. As a <code>Func</code> it is compiled IL you can only run. As an <code>Expression&lt;Func&gt;</code> the compiler builds a tree of objects describing the code, which a library can walk and translate — for example into SQL.</p>
{C(r"""
using System.Linq.Expressions;

Func<Order, bool> asFunc = o => o.Amount > 10_000m;              // executable code
Expression<Func<Order, bool>> asExpr = o => o.Amount > 10_000m;  // data describing the code

Console.WriteLine(asExpr);                     // o => (o.Amount > 10000)
var body = (BinaryExpression)asExpr.Body;
Console.WriteLine(body.NodeType);              // GreaterThan
Console.WriteLine(body.Left);                  // o.Amount
Console.WriteLine(body.Right);                 // 10000

Func<Order, bool> compiled = asExpr.Compile(); // tree → delegate (slow-ish: do it once)
Console.WriteLine(orders.Count(compiled));     // 2

// Expression<Func<Order, bool>> bad = o => { return o.Amount > 0; };
// ❌ CS0834: a lambda with a statement body can't be converted to an expression tree
""", "ExpressionTrees.cs")}
{table(["","Func&lt;Order,bool&gt;","Expression&lt;Func&lt;Order,bool&gt;&gt;"],[
["What it is","A delegate (compiled code)","A tree of Expression objects (data)"],
["Can run directly","Yes","Only after <code>.Compile()</code>"],
["Can be inspected / translated","No","Yes (EF Core → SQL)"],
["Statement bodies, any C# method","Yes","No: single expression; only translatable members for EF"],
["Used by","<code>Enumerable.Where</code> (IEnumerable)","<code>Queryable.Where</code> (IQueryable)"]])}

<h3>5. IEnumerable vs IQueryable (preview of Week 15)</h3>
{C(r"""
// IQueryable<T> : IEnumerable<T> — it adds Expression, ElementType and Provider
IQueryable<Order> query = orders.AsQueryable()
    .Where(o => o.City == "Pune")
    .OrderBy(o => o.Amount);

Console.WriteLine(query.Expression);
// prints the expression tree being built, roughly:
// System.Collections.Generic.List`1[Order].Where(o => (o.City == "Pune")).OrderBy(o => o.Amount)
""")}
{C(r"""
// EF Core (fragment — Week 15). db.Orders is a DbSet<Order>, which is IQueryable<Order>.
var recentPune = await db.Orders
    .Where(o => o.City == "Pune" && o.Amount > 1_000m)   // Expression<Func<…>> → translated to SQL
    .OrderByDescending(o => o.Date)
    .Take(20)
    .ToListAsync();                                       // ONE query runs here
// SELECT TOP(@p) ... FROM [Orders] WHERE [City] = N'Pune' AND [Amount] > 1000.0 ORDER BY [Date] DESC

// ❌ Trap 1: a Func forces Enumerable.Where → loads EVERY row, then filters in memory
Func<Order, bool> isPune = o => o.City == "Pune";
var slow = db.Orders.Where(isPune).ToList();

// ❌ Trap 2: switching to IEnumerable too early does the same
var alsoSlow = db.Orders.AsEnumerable().Where(o => o.City == "Pune").ToList();

// ❌ Trap 3: methods EF can't translate throw at runtime ("could not be translated")
var broken = db.Orders.Where(o => MyHelpers.IsMetroCity(o.City)).ToList();
""", lang="csharp")}
{table(["","IEnumerable&lt;T&gt;","IQueryable&lt;T&gt;"],[
["Namespace / methods","<code>System.Linq.Enumerable</code>","<code>System.Linq.Queryable</code>"],
["Lambdas become","Delegates (Func)","Expression trees"],
["Where it runs","In your process, in memory","Wherever the provider sends it (SQL Server, Cosmos…)"],
["Filtering of DB data","After loading rows","In the database"],
["Can call any C# method","Yes","Only what the provider can translate"],
["Typical source","List, array, iterator","EF Core DbSet, OData"]])}
{tip("Rule for EF Core: keep the query as <code>IQueryable</code> until the last moment, compose Where/Select/OrderBy/Take on it, then materialise once with <code>ToListAsync</code>. Return <code>IQueryable</code> from repositories only if you deliberately want callers to compose queries.")}

<h3>6. LINQ performance tips</h3>
{C(r"""
// 1. Materialise once if you'll enumerate more than once
var delivered = orders.Where(o => o.Status == "Delivered").ToList();
Console.WriteLine($"{delivered.Count} orders, ₹{delivered.Sum(o => o.Amount):N0}");

// 2. Any() instead of Count() > 0 ; the Count property instead of Count() on lists
if (orders.Any(o => o.Status == "Cancelled")) { /* … */ }

// 3. Contains inside Where: HashSet, not List (O(1) vs O(n) per check)
var blockedCities = new HashSet<string>(["Jaipur", "Lucknow"], StringComparer.OrdinalIgnoreCase);
var allowed = orders.Where(o => !blockedCities.Contains(o.City));

// 4. Lookups instead of searching inside a loop (O(n·m) → O(n + m))
// ❌ foreach (var c in customers) { var mine = orders.Where(o => o.Customer == c.Name).ToList(); }
var ordersByCustomer = orders.ToLookup(o => o.Customer);
foreach (var c in customers) { var mine = ordersByCustomer[c.Name]; }

// 5. MinBy/MaxBy instead of sort-then-First
var cheapest = orders.MinBy(o => o.Amount);

// 6. Filter before you sort or project
var top = orders.Where(o => o.Status != "Cancelled").OrderByDescending(o => o.Amount).Take(3);

// 7. Don't ToList() in the middle of a chain "just because" — it allocates a full copy
""", "Performance.cs")}
{table(["Smell","Better"],[
["<code>list.Count() &gt; 0</code>","<code>list.Count &gt; 0</code> or <code>Any()</code>"],
["<code>OrderBy(x).First()</code>","<code>MinBy(x)</code>"],
["<code>Where(p).First()</code>","<code>First(p)</code> (same result, shorter)"],
["<code>list.Where(…).Contains</code> in a loop","Build a HashSet / ToLookup once"],
["Enumerating an IEnumerable parameter 3 times","Accept <code>IReadOnlyList&lt;T&gt;</code> or ToList() once"],
["LINQ inside a per-pixel / per-tick hot loop","A plain for loop over an array or span — measured with BenchmarkDotNet"]])}
<p class="muted">.NET 7 and 8 added SIMD fast paths for Min, Max, Sum and Average over arrays and lists of primitive numbers, so simple aggregates are often faster than a hand-written loop.</p>
''',
["Ending a query with <code>where</code> and no <code>select</code> (query syntax must end with select or group).",
"Writing <code>==</code> instead of <code>equals</code> in a join, or putting the keys on the wrong sides.",
"Passing <code>Func</code> to an EF Core query and loading the whole table.",
"Calling <code>AsEnumerable()</code> or <code>ToList()</code> before filtering a database query.",
"Calling your own C# helper methods inside an EF Core Where clause."],
("40 min", ["Rewrite three of Thursday's method-syntax queries (group by city, inner join on tier, left join) in query syntax and confirm the output is identical.",
"Write <code>Expression&lt;Func&lt;Order, bool&gt;&gt;</code> for \"Pune orders over ₹3,000\", print the tree, walk its Body (BinaryExpression → Left/Right), then Compile and run it on the list.",
"Time (Stopwatch) finding customers' orders for 10,000 customers × 100,000 orders with a nested Where vs ToLookup."]),
[("What does <code>from a in xs from b in ys select …</code> compile to?","A SelectMany call: for each a, enumerate ys and combine each b with a."),
("What's the key difference between Enumerable.Where and Queryable.Where?","Enumerable.Where takes a Func and runs it in memory. Queryable.Where takes an Expression&lt;Func&gt; and adds it to the expression tree for the provider to translate."),
("Why can't EF Core run <code>Where(o =&gt; MyHelper(o))</code>?","MyHelper is arbitrary C# code; the provider sees only a method-call node it has no SQL translation for, so it throws at runtime.")],
[("Basic","Query syntax vs method syntax — which is better?","They're equivalent; query syntax compiles into method calls. Method syntax is more common and covers every operator; query syntax is more readable for joins, let and multiple from clauses. Mixing them is fine."),
("Basic","What does the let keyword do?","Introduces a named intermediate value inside a query that later clauses can use, so you compute it once. The compiler implements it with a Select into an anonymous type (a transparent identifier)."),
("Intermediate","IEnumerable vs IQueryable?","IEnumerable queries run in memory with delegates (LINQ to Objects). IQueryable queries build an expression tree that a provider such as EF Core translates and executes elsewhere (SQL). With a database, IQueryable filters, sorts and pages on the server; switching to IEnumerable early pulls all rows into memory."),
("Intermediate","What is an expression tree and why does EF Core need one?","A data structure representing code as nodes (parameters, member access, binary operators, constants). EF Core needs the tree, not compiled IL, so it can inspect the lambda and translate it into SQL."),
("Intermediate","What is multiple enumeration and how do you avoid it?","Enumerating the same deferred query more than once, which repeats the work (or the database query) and may give different results if the source changed. Avoid it by materialising once with ToList/ToArray, or by accepting IReadOnlyList/IReadOnlyCollection parameters."),
("Intermediate","Give three LINQ performance tips.","Use Any() instead of Count() &gt; 0; use HashSet or ToLookup for repeated membership/lookup checks instead of nested Where/Contains on lists; use MinBy/MaxBy instead of sorting to get one element; filter before sorting; and materialise once when results are reused.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project 5: Student grade analyzer over a CSV",
"Build a console app that reads a class marks CSV, validates each row, models students with records, and uses LINQ to report class averages, subject toppers, grade distribution, failures and a rank list. Budget: about 4 hours.",
[("CSV","Comma-separated values: a header row of column names, then one record per line."),
("Parsing vs validation","Parsing turns text into typed values; validation checks the values make sense (marks 0–100, unique roll numbers)."),
("Pass mark","The minimum marks per subject to pass; 33 out of 100, as on CBSE boards."),
("Competition ranking","\"1-2-2-4\" ranking: tied students share a rank and the next rank is skipped."),
("Grade band","A percentage range mapped to a grade, e.g. 91–100 → A1.")],
["Records (<code>Student</code>, <code>Mark</code>) hold data; a static parser builds them; a report class queries them.",
"Bad rows are reported with their line number and skipped — one typo shouldn't kill the whole report.",
"Subjects come from the header, so adding a column needs no code change.",
"All reports are LINQ over an <code>IReadOnlyList&lt;Student&gt;</code> — no loops except the ranking.",
"Core has no Console calls; the App does all printing. Tomorrow you'll add 10 more reports."],
f'''
<h3>Requirements</h3>
<ul>
<li>Input: <code>students.csv</code> with columns <code>RollNo,Name,Class,Section</code> followed by one column per subject (marks out of 100).</li>
<li>Skip blank lines. Report and skip rows with the wrong number of columns, non-numeric or out-of-range marks, or duplicate roll numbers. Stop with a clear error if the header is wrong.</li>
<li>Per student: total, percentage (2 decimals), grade by percentage (A1 ≥ 91, A2 ≥ 81, B1 ≥ 71, B2 ≥ 61, C1 ≥ 51, C2 ≥ 41, D ≥ 33, E below), and PASS/FAIL (fail if any subject is below 33).</li>
<li>Reports: class-section averages with pass %, toppers per subject (all tied toppers), grade distribution including zero counts, failures with failed subjects, rank list with competition ranking.</li>
<li>File path from the first command-line argument, defaulting to the CSV copied next to the executable.</li>
</ul>

<h3>Scaffold</h3>
{C(r"""
mkdir GradeAnalyzer && cd GradeAnalyzer
dotnet new sln -n GradeAnalyzer
dotnet new classlib -n GradeAnalyzer.Core
dotnet new console  -n GradeAnalyzer.App
dotnet sln add GradeAnalyzer.Core GradeAnalyzer.App
dotnet add GradeAnalyzer.App reference GradeAnalyzer.Core
rm GradeAnalyzer.Core/Class1.cs
dotnet new gitignore
""", lang="bash")}
{C(r"""
GradeAnalyzer/
├─ GradeAnalyzer.sln
├─ GradeAnalyzer.Core/
│  ├─ Grading.cs
│  ├─ Models/
│  │  ├─ Mark.cs
│  │  └─ Student.cs
│  ├─ Parsing/
│  │  └─ CsvStudentParser.cs
│  └─ Reports/
│     ├─ ReportModels.cs
│     └─ GradeReports.cs
└─ GradeAnalyzer.App/
   ├─ GradeAnalyzer.App.csproj
   ├─ students.csv
   └─ Program.cs
""", lang="text")}

<h3>Step 1 — Sample data</h3>
<p>Line 17 is deliberately broken (<code>x</code> in Science) so you can see the validation working.</p>
{C(r"""
RollNo,Name,Class,Section,Maths,Science,English,Hindi,SocialScience
101,Aarav Sharma,10,A,95,88,76,82,90
102,Diya Patel,10,A,78,92,89,85,80
103,Kabir Singh,10,A,45,38,52,30,48
104,Ananya Iyer,10,A,99,95,91,88,94
105,Rohan Gupta,10,A,62,58,70,66,55
106,Ishita Reddy,10,B,88,79,95,90,86
107,Vihaan Mehta,10,B,28,35,40,45,31
108,Saanvi Nair,10,B,91,97,84,79,88
109,Arjun Verma,10,B,73,68,61,72,70
110,Meera Joshi,10,B,99,85,78,81,83
111,Kunal Desai,9,A,55,61,49,58,63
112,Priya Menon,9,A,84,90,93,87,91
113,Aditya Rao,9,A,31,42,38,29,35
114,Neha Kulkarni,9,A,76,74,80,83,79
115,Farhan Khan,9,A,92,88,85,76,90
116,Tanvi Bose,9,A,88,x,90,85,80
""", "GradeAnalyzer.App/students.csv", lang="text")}
<p>Copy the CSV to the output folder so the app finds it wherever you run it from:</p>
{C(r"""
<ItemGroup>
  <None Update="students.csv" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
""", "GradeAnalyzer.App/GradeAnalyzer.App.csproj (add inside <Project>)", lang="xml")}

<h3>Step 2 — Grading rules</h3>
{C(r"""
namespace GradeAnalyzer.Core;

public static class Grading
{
    public const int PassMark = 33;
    public const int MaxMarks = 100;

    public static readonly IReadOnlyList<string> AllGrades = ["A1", "A2", "B1", "B2", "C1", "C2", "D", "E"];

    public static string GradeFor(decimal percentage) => percentage switch
    {
        >= 91m => "A1",
        >= 81m => "A2",
        >= 71m => "B1",
        >= 61m => "B2",
        >= 51m => "C1",
        >= 41m => "C2",
        >= 33m => "D",
        _      => "E"
    };
}
""", "GradeAnalyzer.Core/Grading.cs")}

<h3>Step 3 — Records for Mark and Student</h3>
{C(r"""
namespace GradeAnalyzer.Core.Models;

public sealed record Mark(string Subject, int Score)
{
    public bool IsPass => Score >= Grading.PassMark;
}
""", "GradeAnalyzer.Core/Models/Mark.cs")}
{C(r"""
namespace GradeAnalyzer.Core.Models;

public sealed record Student(int RollNo, string Name, string ClassName, string Section, IReadOnlyList<Mark> Marks)
{
    public string ClassSection => $"{ClassName}-{Section}";

    public int Total => Marks.Sum(m => m.Score);

    // Every subject is out of 100, so percentage = total / number of subjects
    public decimal Percentage => Marks.Count == 0 ? 0m : Math.Round((decimal)Total / Marks.Count, 2);

    public string Grade => Grading.GradeFor(Percentage);

    public IEnumerable<Mark> FailedSubjects => Marks.Where(m => !m.IsPass);

    public bool HasFailed => Marks.Any(m => !m.IsPass);

    public int ScoreIn(string subject) =>
        Marks.First(m => m.Subject.Equals(subject, StringComparison.OrdinalIgnoreCase)).Score;
}
""", "GradeAnalyzer.Core/Models/Student.cs")}
{warn("Record equality compares <code>Marks</code> by reference (it's a list), so two students with identical data but different list instances are not equal. That's fine here — we identify students by RollNo — but remember it before putting records with collections in a HashSet.", "Note")}

<h3>Step 4 — CSV parser with line-level errors</h3>
{C(r"""
using GradeAnalyzer.Core.Models;

namespace GradeAnalyzer.Core.Parsing;

public sealed record ParseError(int LineNumber, string Line, string Reason);

public sealed record ParseResult(
    IReadOnlyList<Student> Students,
    IReadOnlyList<string> Subjects,
    IReadOnlyList<ParseError> Errors);

public static class CsvStudentParser
{
    private static readonly string[] FixedColumns = ["RollNo", "Name", "Class", "Section"];

    public static ParseResult ParseFile(string path) => Parse(File.ReadLines(path));

    public static ParseResult Parse(IEnumerable<string> lines)
    {
        // Keep original line numbers for error messages, then drop blank lines
        var numbered = lines
            .Select((text, index) => (Number: index + 1, Text: text.Trim()))
            .Where(l => l.Text.Length > 0)
            .ToList();

        if (numbered.Count == 0)
            throw new FormatException("The file is empty.");

        string[] header = numbered[0].Text.Split(',', StringSplitOptions.TrimEntries);
        bool headerOk = header.Length > FixedColumns.Length &&
                        header.Take(FixedColumns.Length).SequenceEqual(FixedColumns, StringComparer.OrdinalIgnoreCase);
        if (!headerOk)
            throw new FormatException($"Header must start with {string.Join(",", FixedColumns)} followed by at least one subject.");

        string[] subjects = header[FixedColumns.Length..];
        if (subjects.Distinct(StringComparer.OrdinalIgnoreCase).Count() != subjects.Length)
            throw new FormatException("Each subject column must appear only once.");

        var students = new List<Student>();
        var errors = new List<ParseError>();
        var seenRollNos = new HashSet<int>();

        foreach (var (number, text) in numbered.Skip(1))
        {
            string? problem = TryParseRow(text, subjects, out Student? student);

            if (problem is not null)
                errors.Add(new ParseError(number, text, problem));
            else if (!seenRollNos.Add(student!.RollNo))
                errors.Add(new ParseError(number, text, $"Duplicate roll number {student.RollNo}"));
            else
                students.Add(student);
        }

        return new ParseResult(students, subjects, errors);
    }

    // Returns null on success, or a reason the row was rejected
    private static string? TryParseRow(string text, string[] subjects, out Student? student)
    {
        student = null;
        string[] cells = text.Split(',', StringSplitOptions.TrimEntries);

        int expected = FixedColumns.Length + subjects.Length;
        if (cells.Length != expected)
            return $"Expected {expected} columns, found {cells.Length}";

        if (!int.TryParse(cells[0], out int rollNo) || rollNo <= 0)
            return $"Invalid roll number '{cells[0]}'";
        if (cells[1].Length == 0)
            return "Name is empty";
        if (cells[2].Length == 0 || cells[3].Length == 0)
            return "Class or section is empty";

        var marks = new List<Mark>(subjects.Length);
        for (int i = 0; i < subjects.Length; i++)
        {
            string raw = cells[FixedColumns.Length + i];
            if (!int.TryParse(raw, out int score))
                return $"{subjects[i]}: '{raw}' is not a number";
            if (score is < 0 or > Grading.MaxMarks)
                return $"{subjects[i]}: {score} is outside 0–{Grading.MaxMarks}";
            marks.Add(new Mark(subjects[i], score));
        }

        student = new Student(rollNo, cells[1], cells[2], cells[3].ToUpperInvariant(), marks);
        return null;
    }
}
""", "GradeAnalyzer.Core/Parsing/CsvStudentParser.cs")}
<p>This simple <code>Split(',')</code> doesn't support quoted fields like <code>"Iyer, Ananya"</code>. That's acceptable for a file you control; for real CSV from Excel use a library such as CsvHelper (Week 6).</p>

<h3>Step 5 — Report models and the LINQ reports</h3>
{C(r"""
using GradeAnalyzer.Core.Models;

namespace GradeAnalyzer.Core.Reports;

public sealed record ClassAverage(string ClassSection, int Students, decimal AveragePercentage, decimal PassRate);
public sealed record SubjectTopper(string Subject, int Score, IReadOnlyList<string> Names);
public sealed record GradeCount(string Grade, int Count);
public sealed record FailureEntry(Student Student, IReadOnlyList<Mark> FailedSubjects);
public sealed record RankEntry(int Rank, Student Student);
""", "GradeAnalyzer.Core/Reports/ReportModels.cs")}
{C(r"""
using GradeAnalyzer.Core.Models;

namespace GradeAnalyzer.Core.Reports;

public class GradeReports(IReadOnlyList<Student> students, IReadOnlyList<string> subjects)
{
    // GroupBy + Average + Count(predicate)
    public IReadOnlyList<ClassAverage> ClassAverages() =>
        students
            .GroupBy(s => s.ClassSection)
            .OrderBy(g => g.Key, StringComparer.Ordinal)
            .Select(g => new ClassAverage(
                g.Key,
                g.Count(),
                Math.Round(g.Average(s => s.Percentage), 2),
                Math.Round(100m * g.Count(s => !s.HasFailed) / g.Count(), 1)))
            .ToList();

    // Max, then Where to keep every student who tied for the top score
    public IReadOnlyList<SubjectTopper> SubjectToppers() =>
        subjects
            .Select(subject =>
            {
                int best = students.Max(s => s.ScoreIn(subject));
                var names = students.Where(s => s.ScoreIn(subject) == best).Select(s => s.Name).ToList();
                return new SubjectTopper(subject, best, names);
            })
            .ToList();

    // GroupBy → dictionary, then project over ALL grades so empty grades show 0
    public IReadOnlyList<GradeCount> GradeDistribution()
    {
        Dictionary<string, int> counts = students
            .GroupBy(s => s.Grade)
            .ToDictionary(g => g.Key, g => g.Count());

        return Grading.AllGrades
            .Select(grade => new GradeCount(grade, counts.GetValueOrDefault(grade)))
            .ToList();
    }

    public IReadOnlyList<FailureEntry> Failures() =>
        students
            .Where(s => s.HasFailed)
            .OrderBy(s => s.ClassSection, StringComparer.Ordinal)
            .ThenBy(s => s.RollNo)
            .Select(s => new FailureEntry(s, s.FailedSubjects.ToList()))
            .ToList();

    // Competition ranking (1, 2, 2, 4): sort once, then one pass comparing with the previous student
    public IReadOnlyList<RankEntry> RankList()
    {
        List<Student> ordered = students
            .OrderByDescending(s => s.Total)
            .ThenBy(s => s.Name, StringComparer.Ordinal)
            .ToList();

        var ranks = new List<RankEntry>(ordered.Count);
        for (int i = 0; i < ordered.Count; i++)
        {
            bool tiedWithPrevious = i > 0 && ordered[i].Total == ordered[i - 1].Total;
            int rank = tiedWithPrevious ? ranks[i - 1].Rank : i + 1;
            ranks.Add(new RankEntry(rank, ordered[i]));
        }
        return ranks;
    }
}
""", "GradeAnalyzer.Core/Reports/GradeReports.cs")}
{tip("A one-line LINQ ranking exists — <code>students.Select(s =&gt; new RankEntry(1 + students.Count(o =&gt; o.Total &gt; s.Total), s))</code> — but it's O(n²). Fine for a class of 40, slow for a board of 2 lakh students. Know both and say which you'd pick.")}

<h3>Step 6 — Program.cs</h3>
{C(r"""
using GradeAnalyzer.Core.Parsing;
using GradeAnalyzer.Core.Reports;

Console.OutputEncoding = System.Text.Encoding.UTF8;   // for ⚠ ✗ █ on Windows terminals

string path = args.Length > 0 ? args[0] : Path.Combine(AppContext.BaseDirectory, "students.csv");
if (!File.Exists(path))
{
    Console.WriteLine($"✗ File not found: {path}");
    return 1;
}

ParseResult data;
try
{
    data = CsvStudentParser.ParseFile(path);
}
catch (FormatException ex)
{
    Console.WriteLine($"✗ {ex.Message}");
    return 1;
}

foreach (var error in data.Errors)
    Console.WriteLine($"  ⚠ Line {error.LineNumber} skipped: {error.Reason}");

if (data.Students.Count == 0)
{
    Console.WriteLine("✗ No valid student rows found.");
    return 1;
}

Console.WriteLine($"Loaded {data.Students.Count} students · subjects: {string.Join(", ", data.Subjects)}");
var reports = new GradeReports(data.Students, data.Subjects);

Heading("Class averages");
Console.WriteLine($"  {"Class",-7}{"Students",8}{"Avg %",9}{"Pass %",9}");
foreach (var c in reports.ClassAverages())
    Console.WriteLine($"  {c.ClassSection,-7}{c.Students,8}{c.AveragePercentage,9:N2}{c.PassRate,9:N1}");

Heading("Toppers per subject");
foreach (var t in reports.SubjectToppers())
    Console.WriteLine($"  {t.Subject,-14}{t.Score,4}  {string.Join(", ", t.Names)}");

Heading("Grade distribution");
foreach (var g in reports.GradeDistribution())
    Console.WriteLine($"  {g.Grade,-3}{g.Count,3}  {new string('█', g.Count)}");

Heading("Failures (below 33 in any subject)");
foreach (var f in reports.Failures())
{
    string failed = string.Join(", ", f.FailedSubjects.Select(m => $"{m.Subject} {m.Score}"));
    Console.WriteLine($"  {f.Student.ClassSection,-6}{f.Student.RollNo,4}  {f.Student.Name,-15}{failed}");
}

Heading("Rank list");
Console.WriteLine($"  {"Rank",4}  {"Roll",4}  {"Name",-15}{"Class",-6}{"Total",6}{"%",8}  {"Grade",-6}Result");
foreach (var (rank, s) in reports.RankList())
{
    string result = s.HasFailed ? "FAIL" : "PASS";
    Console.WriteLine($"  {rank,4}  {s.RollNo,4}  {s.Name,-15}{s.ClassSection,-6}{s.Total,6}{s.Percentage,8:N2}  {s.Grade,-6}{result}");
}

return 0;

static void Heading(string title)
{
    Console.WriteLine();
    Console.WriteLine($"== {title} ==");
}
""", "GradeAnalyzer.App/Program.cs")}

<h3>Run it</h3>
{C(r"""
dotnet run --project GradeAnalyzer.App
# or with your own file:
dotnet run --project GradeAnalyzer.App -- ./data/term1.csv
""", lang="bash")}
{C(r"""
  ⚠ Line 17 skipped: Science: 'x' is not a number
Loaded 15 students · subjects: Maths, Science, English, Hindi, SocialScience

== Class averages ==
  Class  Students    Avg %   Pass %
  10-A          5    73.84     80.0
  10-B          5    73.04     80.0
  9-A           5    69.16     80.0

== Toppers per subject ==
  Maths           99  Ananya Iyer, Meera Joshi
  Science         97  Saanvi Nair
  English         95  Ishita Reddy
  Hindi           90  Ishita Reddy
  SocialScience   94  Ananya Iyer

== Grade distribution ==
  A1   1  █
  A2   7  ███████
  B1   1  █
  B2   2  ██
  C1   1  █
  C2   1  █
  D    2  ██
  E    0

== Failures (below 33 in any subject) ==
  10-A   103  Kabir Singh    Hindi 30
  10-B   107  Vihaan Mehta   Maths 28, SocialScience 31
  9-A    113  Aditya Rao     Maths 31, Hindi 29

== Rank list ==
  Rank  Roll  Name           Class  Total       %  Grade Result
     1   104  Ananya Iyer    10-A     467   93.40  A1    PASS
     2   112  Priya Menon    9-A      445   89.00  A2    PASS
     3   108  Saanvi Nair    10-B     439   87.80  A2    PASS
     4   106  Ishita Reddy   10-B     438   87.60  A2    PASS
     5   101  Aarav Sharma   10-A     431   86.20  A2    PASS
     5   115  Farhan Khan    9-A      431   86.20  A2    PASS
     7   110  Meera Joshi    10-B     426   85.20  A2    PASS
     8   102  Diya Patel     10-A     424   84.80  A2    PASS
     9   114  Neha Kulkarni  9-A      392   78.40  B1    PASS
    10   109  Arjun Verma    10-B     344   68.80  B2    PASS
    11   105  Rohan Gupta    10-A     311   62.20  B2    PASS
    12   111  Kunal Desai    9-A      286   57.20  C1    PASS
    13   103  Kabir Singh    10-A     213   42.60  C2    FAIL
    14   107  Vihaan Mehta   10-B     179   35.80  D     FAIL
    15   113  Aditya Rao     9-A      175   35.00  D     FAIL
""", lang="text")}
<p>Notice Aarav and Farhan share rank 5 and rank 6 is skipped. Kabir has a C2 grade by percentage but still fails because of Hindi — grade and result are separate rules, as on real mark sheets.</p>

<h3>Stretch goals</h3>
<ul>
<li>Accept a <code>--pass-mark 35</code> argument (some state boards use 35) and pass it into the reports instead of the constant.</li>
<li>Add a per-subject grade (A1–E for each mark) and print a full mark sheet for one roll number.</li>
<li>Support dense ranking (1, 2, 2, 3) behind an option and compare with competition ranking.</li>
<li>Write unit-test-style checks in a scratch console app: a file with only a header, a duplicate roll number, a mark of 101 (you'll move them to xUnit in Week 10).</li>
</ul>
''',
iqs=[("Basic","Why are Student and Mark records?","They're data carriers created once from the CSV and never modified. Records give concise positional syntax, immutability by default, value-based equality and a readable ToString for debugging."),
("Basic","Why does the parser collect errors instead of throwing on the first bad row?","One typo shouldn't block a whole class's report. Row-level problems are expected input errors, so they're returned with line numbers; only a structural problem (empty file, wrong header) throws, because nothing useful can be done then."),
("Intermediate","How do you report all tied toppers, not just one?","Compute the maximum score per subject, then filter with Where for everyone equal to it. MaxBy alone would return only the first student with the top score."),
("Intermediate","Your rank list must handle 2 lakh students. What changes?","Keep the sort-once, single-pass ranking (O(n log n)) rather than counting higher scores per student (O(n²)); stream the CSV row by row (File.ReadLines is lazy, but Parse currently calls ToList() on all lines, so process rows as they arrive instead); and cache computed properties like Total if profiling shows the repeated Sum matters.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Add 10 LINQ reports, harden the analyzer, README and revision",
"Extend the analyzer with ten more LINQ reports behind a menu built from delegates, try to break it, document and push it, then revise the week.",
[("Pivot","Turning row values (sections) into columns, e.g. subject × section average table."),
("Compartment","A student who failed exactly one subject and may reappear in it (CBSE term)."),
("All-rounder","Here: a student above their section's average in every subject."),
("Standard deviation","How spread out a student's marks are; a low value means consistent performance."),
("Histogram","Counts of values falling into equal-width bands, e.g. 0–9, 10–19, … 90–100.")],
["Each report is one public method returning records — easy to test and to print differently later.",
"The menu is a <code>Dictionary&lt;int, (string, Action)&gt;</code>: Monday's \"delegates as strategy\" in action.",
"The printing helpers are local functions capturing <code>data</code> and <code>advanced</code>: Tuesday's closures.",
"Most of the core LINQ operators from Wednesday and Thursday (GroupBy, ToLookup, GroupJoin, Zip, Aggregate, MinBy/MaxBy…) appear below."],
f'''
<h3>1. Plan for today (≈4 hours)</h3>
{table(["Time","Activity"],[
["90 min","Implement the 10 reports below and the menu"],
["30 min","Try-to-break table; fix what breaks"],
["20 min","README and push"],
["60 min","Revision checklist, quiz, interview questions aloud"],
["20 min","Write your own LINQ cheat sheet in <code>dotnet-notes/week05.md</code>"]])}

<h3>2. The 10 reports</h3>
{table(["#","Report","LINQ used"],[
["1","Subject averages by section (pivot)","GroupBy, ToDictionary, Average"],
["2","Strongest section in each subject","GroupBy, Select, MaxBy"],
["3","Top N per section","ToLookup, OrderByDescending, ThenBy, Take"],
["4","Compartment list (failed exactly one subject)","Where, Count"],
["5","Strongest and weakest subject per student","MaxBy, MinBy, OrderByDescending"],
["6","Pass rate per subject","Select, Count(predicate)"],
["7","All-rounders (above section average in every subject)","GroupBy, nested ToDictionary, All"],
["8","Score histogram for a subject","Range, GroupJoin (keeps empty bands)"],
["9","Most consistent students","Average, Aggregate, OrderBy, Take"],
["10","Section head-to-head by rank","Where, OrderByDescending, Zip, Select with index"]])}
{C(r"""
using GradeAnalyzer.Core.Models;

namespace GradeAnalyzer.Core.Reports;

public sealed record SectionSubjectAverages(string ClassSection, IReadOnlyDictionary<string, decimal> Averages);
public sealed record SectionLeader(string Subject, string ClassSection, decimal Average);
public sealed record SectionToppers(string ClassSection, IReadOnlyList<Student> Top);

public sealed record SubjectSpread(Student Student, Mark Strongest, Mark Weakest)
{
    public int Gap => Strongest.Score - Weakest.Score;
}

public sealed record SubjectPassRate(string Subject, int Passed, int Appeared)
{
    public decimal Percent => Appeared == 0 ? 0m : Math.Round(100m * Passed / Appeared, 1);
}

public sealed record ScoreBand(int From, int To, int Count)
{
    public string Label => $"{From}–{To}";
}

public sealed record Consistency(Student Student, double Mean, double StdDev);

public sealed record HeadToHeadRow(int Position, Student A, Student B)
{
    public string Leader => A.Total == B.Total ? "tie" : A.Total > B.Total ? A.ClassSection : B.ClassSection;
}
""", "GradeAnalyzer.Core/Reports/AdvancedReportModels.cs")}
{C(r"""
using GradeAnalyzer.Core.Models;

namespace GradeAnalyzer.Core.Reports;

public class AdvancedReports(IReadOnlyList<Student> students, IReadOnlyList<string> subjects)
{
    // 1. Pivot: one row per section, one average per subject
    public IReadOnlyList<SectionSubjectAverages> SubjectAveragesBySection() =>
        students
            .GroupBy(s => s.ClassSection)
            .OrderBy(g => g.Key, StringComparer.Ordinal)
            .Select(g => new SectionSubjectAverages(
                g.Key,
                subjects.ToDictionary(
                    sub => sub,
                    sub => Math.Round((decimal)g.Average(s => s.ScoreIn(sub)), 1))))
            .ToList();

    // 2. Which section leads each subject (ties: MaxBy keeps the first section seen)
    public IReadOnlyList<SectionLeader> BestSectionPerSubject() =>
        subjects
            .Select(sub => students
                .GroupBy(s => s.ClassSection)
                .Select(g => new SectionLeader(sub, g.Key, Math.Round((decimal)g.Average(s => s.ScoreIn(sub)), 1)))
                .MaxBy(x => x.Average)!)
            .ToList();

    // 3. Top N per section using a lookup (built once, immediate)
    public IReadOnlyList<SectionToppers> TopPerSection(int n = 3)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(n);
        ILookup<string, Student> bySection = students.ToLookup(s => s.ClassSection);

        return bySection
            .OrderBy(g => g.Key, StringComparer.Ordinal)
            .Select(g => new SectionToppers(
                g.Key,
                g.OrderByDescending(s => s.Total).ThenBy(s => s.Name, StringComparer.Ordinal).Take(n).ToList()))
            .ToList();
    }

    // 4. Compartment: failed exactly one subject
    public IReadOnlyList<FailureEntry> Compartment() =>
        students
            .Where(s => s.FailedSubjects.Count() == 1)
            .Select(s => new FailureEntry(s, s.FailedSubjects.ToList()))
            .ToList();

    // 5. Strongest and weakest subject for every student, biggest gap first
    public IReadOnlyList<SubjectSpread> StrongestAndWeakest() =>
        students
            .Select(s => new SubjectSpread(s, s.Marks.MaxBy(m => m.Score)!, s.Marks.MinBy(m => m.Score)!))
            .OrderByDescending(x => x.Gap)
            .ToList();

    // 6. Pass percentage per subject, weakest subject first
    public IReadOnlyList<SubjectPassRate> PassRateBySubject() =>
        subjects
            .Select(sub => new SubjectPassRate(
                sub,
                students.Count(s => s.ScoreIn(sub) >= Grading.PassMark),
                students.Count))
            .OrderBy(r => r.Percent)
            .ToList();

    // 7. All-rounders: strictly above their own section's average in EVERY subject
    public IReadOnlyList<Student> AllRounders()
    {
        // section → (subject → average), computed once
        Dictionary<string, Dictionary<string, double>> averages = students
            .GroupBy(s => s.ClassSection)
            .ToDictionary(
                g => g.Key,
                g => subjects.ToDictionary(sub => sub, sub => g.Average(s => s.ScoreIn(sub))));

        return students
            .Where(s => subjects.All(sub => s.ScoreIn(sub) > averages[s.ClassSection][sub]))
            .OrderBy(s => s.ClassSection, StringComparer.Ordinal)
            .ThenBy(s => s.RollNo)
            .ToList();
    }

    // 8. Histogram of one subject in bands of 10; GroupJoin keeps bands with zero students
    public IReadOnlyList<ScoreBand> ScoreBands(string subject)
    {
        IEnumerable<int> bandStarts = Enumerable.Range(0, 10).Select(i => i * 10);   // 0, 10, … 90

        return bandStarts
            .GroupJoin(
                students,
                start => start,
                s => Math.Min(s.ScoreIn(subject) / 10 * 10, 90),       // 100 belongs to the 90–100 band
                (start, inBand) => new ScoreBand(start, start == 90 ? 100 : start + 9, inBand.Count()))
            .ToList();
    }

    // 9. Most consistent: lowest standard deviation of a student's marks
    public IReadOnlyList<Consistency> MostConsistent(int n = 3) =>
        students
            .Select(s =>
            {
                double mean = s.Marks.Average(m => m.Score);
                double sumOfSquares = s.Marks.Aggregate(0.0, (acc, m) => acc + Math.Pow(m.Score - mean, 2));
                return new Consistency(s, mean, Math.Sqrt(sumOfSquares / s.Marks.Count));
            })
            .OrderBy(c => c.StdDev)
            .Take(n)
            .ToList();

    // 10. Rank k of section A vs rank k of section B; Zip stops at the smaller section
    public IReadOnlyList<HeadToHeadRow> SectionHeadToHead(string sectionA, string sectionB)
    {
        IEnumerable<Student> Ranked(string section) =>
            students
                .Where(s => s.ClassSection.Equals(section, StringComparison.OrdinalIgnoreCase))
                .OrderByDescending(s => s.Total)
                .ThenBy(s => s.Name, StringComparer.Ordinal);

        return Ranked(sectionA)
            .Zip(Ranked(sectionB))
            .Select((pair, index) => new HeadToHeadRow(index + 1, pair.First, pair.Second))
            .ToList();
    }
}
""", "GradeAnalyzer.Core/Reports/AdvancedReports.cs")}
{tip("Report 7 computes the averages dictionary <b>once</b> before the Where. Computing <code>g.Average(...)</code> inside the <code>All</code> lambda would recompute it for every student × subject — the \"lookup instead of nested query\" tip from Friday.")}

<h3>3. A menu built from delegates</h3>
<p>Keep Saturday's loading code (everything up to <code>var reports = …</code>), move Saturday's printing into a local function <code>PrintCoreReports()</code>, and replace the rest of <code>Program.cs</code> with this:</p>
{C(r"""
var advanced = new AdvancedReports(data.Students, data.Subjects);

// Monday: delegates as strategies. Each menu entry is a title plus an Action.
var menu = new Dictionary<int, (string Title, Action Run)>
{
    [1]  = ("Subject averages by section",       PrintSectionAverages),
    [2]  = ("Strongest section per subject",     PrintBestSections),
    [3]  = ("Top 3 per section",                 () => PrintTopPerSection(3)),
    [4]  = ("Compartment (failed one subject)",  PrintCompartment),
    [5]  = ("Strongest / weakest subject",       PrintSpread),
    [6]  = ("Pass rate per subject",             PrintPassRates),
    [7]  = ("All-rounders",                      PrintAllRounders),
    [8]  = ("Score histogram",                   PrintHistogram),
    [9]  = ("Most consistent students",          PrintConsistency),
    [10] = ("Section head-to-head",              PrintHeadToHead),
    [11] = ("Saturday's core reports",           PrintCoreReports),
};

while (true)
{
    Console.WriteLine();
    foreach (var (key, (title, _)) in menu)
        Console.WriteLine($"  {key,2}) {title}");
    Console.WriteLine("   0) Exit");
    Console.Write("Choose: ");

    string? input = Console.ReadLine();
    if (input is null || input.Trim() == "0") break;

    if (int.TryParse(input, out int choice) && menu.TryGetValue(choice, out var entry))
    {
        Heading(entry.Title);
        entry.Run();
    }
    else
    {
        Console.WriteLine("  ✗ Pick a number from the menu.");
    }
}
return 0;

// Tuesday: local functions that capture `data` and `advanced` (closures)
void PrintSectionAverages()
{
    var rows = advanced.SubjectAveragesBySection();
    Console.WriteLine($"  {"Subject",-14}" + string.Concat(rows.Select(r => $"{r.ClassSection,7}")));
    foreach (string sub in data.Subjects)
        Console.WriteLine($"  {sub,-14}" + string.Concat(rows.Select(r => $"{r.Averages[sub],7:N1}")));
}

void PrintBestSections()
{
    foreach (var x in advanced.BestSectionPerSubject())
        Console.WriteLine($"  {x.Subject,-14}{x.ClassSection,-6}{x.Average,6:N1}");
}

void PrintTopPerSection(int n)
{
    foreach (var section in advanced.TopPerSection(n))
        Console.WriteLine($"  {section.ClassSection,-6}{string.Join(", ", section.Top.Select(s => $"{s.Name} ({s.Total})"))}");
}

void PrintCompartment()
{
    var list = advanced.Compartment();
    if (list.Count == 0) { Console.WriteLine("  Nobody — well done!"); return; }
    foreach (var f in list)
        Console.WriteLine($"  {f.Student.RollNo} {f.Student.Name,-15} reappear in {f.FailedSubjects[0].Subject} ({f.FailedSubjects[0].Score})");
}

void PrintSpread()
{
    foreach (var x in advanced.StrongestAndWeakest().Take(5))
        Console.WriteLine($"  {x.Student.Name,-15} best {x.Strongest.Subject} {x.Strongest.Score}, weakest {x.Weakest.Subject} {x.Weakest.Score} (gap {x.Gap})");
}

void PrintPassRates()
{
    foreach (var r in advanced.PassRateBySubject())
        Console.WriteLine($"  {r.Subject,-14}{r.Passed,3}/{r.Appeared,-3}{r.Percent,7:N1}%");
}

void PrintAllRounders()
{
    foreach (var s in advanced.AllRounders())
        Console.WriteLine($"  {s.ClassSection,-6}{s.RollNo,4}  {s.Name}");
}

void PrintHistogram()
{
    Console.Write($"  Subject ({string.Join("/", data.Subjects)}): ");
    string? subject = Console.ReadLine()?.Trim();
    string? match = data.Subjects.FirstOrDefault(s => s.Equals(subject, StringComparison.OrdinalIgnoreCase));
    if (match is null) { Console.WriteLine("  ✗ Unknown subject"); return; }

    foreach (var band in advanced.ScoreBands(match))
        Console.WriteLine($"  {band.Label,-8}{band.Count,3}  {new string('█', band.Count)}");
}

void PrintConsistency()
{
    foreach (var c in advanced.MostConsistent())
        Console.WriteLine($"  {c.Student.Name,-15}{c.Mean,7:N1}{c.StdDev,8:N2}");
}

void PrintHeadToHead()
{
    Console.Write("  First section (e.g. 10-A): ");
    string a = Console.ReadLine()?.Trim() ?? "";
    Console.Write("  Second section (e.g. 10-B): ");
    string b = Console.ReadLine()?.Trim() ?? "";

    var rows = advanced.SectionHeadToHead(a, b);
    if (rows.Count == 0) { Console.WriteLine("  ✗ One of those sections has no students"); return; }
    foreach (var r in rows)
        Console.WriteLine($"  {r.Position,3}. {r.A.Name,-15}{r.A.Total,4}   vs   {r.B.Name,-15}{r.B.Total,4}   → {r.Leader}");
}

void PrintCoreReports()
{
    // Saturday's five report blocks go here unchanged
}

static void Heading(string title)
{
    Console.WriteLine();
    Console.WriteLine($"== {title} ==");
}
""", "GradeAnalyzer.App/Program.cs (menu)")}
<p>The <code>foreach (var (key, (title, _)) in menu)</code> line deconstructs each <code>KeyValuePair</code>, then the tuple value inside it, discarding the Action. Dictionary enumeration order isn't guaranteed in general; for a dictionary built once and never modified it follows insertion order in practice, but use a <code>SortedDictionary</code> if order must be guaranteed.</p>

<h3>4. Sample output</h3>
{C(r"""
== Subject averages by section ==
  Subject          10-A   10-B    9-A
  Maths            75.8   75.8   67.6
  Science          74.2   72.8   71.0
  English          75.6   71.6   69.0
  Hindi            70.2   73.4   66.6
  SocialScience    73.4   71.6   71.6

== Strongest section per subject ==
  Maths         10-A    75.8        ← tied with 10-B; MaxBy keeps the first
  Science       10-A    74.2
  English       10-A    75.6
  Hindi         10-B    73.4
  SocialScience 10-A    73.4

== Compartment (failed one subject) ==
  103 Kabir Singh     reappear in Hindi (30)

== Pass rate per subject ==
  Maths          13/15    86.7%
  Hindi          13/15    86.7%
  SocialScience  14/15    93.3%
  Science        15/15   100.0%
  English        15/15   100.0%

== Score histogram ==
  Subject (Maths/Science/English/Hindi/SocialScience): maths
  0–9       0
  10–19     0
  20–29     1  █
  30–39     1  █
  40–49     1  █
  50–59     1  █
  60–69     1  █
  70–79     3  ███
  80–89     2  ██
  90–100    5  █████

== Most consistent students ==
  Neha Kulkarni     78.4    3.14
  Priya Menon       89.0    3.16
  Ananya Iyer       93.4    3.72

== Section head-to-head ==
  First section (e.g. 10-A): 10-a
  Second section (e.g. 10-B): 10-B
    1. Ananya Iyer     467   vs   Saanvi Nair     439   → 10-A
    2. Aarav Sharma    431   vs   Ishita Reddy    438   → 10-B
    3. Diya Patel      424   vs   Meera Joshi     426   → 10-B
    4. Rohan Gupta     311   vs   Arjun Verma     344   → 10-B
    5. Kabir Singh     213   vs   Vihaan Mehta    179   → 10-A
""", lang="text")}
<p>All-rounders with this data: Aarav, Diya, Ananya (10-A), Ishita, Saanvi, Meera (10-B), Priya, Neha, Farhan (9-A).</p>

<h3>5. Try to break it</h3>
{table(["Scenario","Expected"],[
["File doesn't exist","\"✗ File not found: …\", exit code 1"],
["Empty file / only blank lines","\"✗ The file is empty.\""],
["Header only, no student rows","\"✗ No valid student rows found.\""],
["Header <code>Roll,Name,…</code> (wrong first column)","Header error, nothing parsed"],
["Two <code>Maths</code> columns","\"Each subject column must appear only once.\""],
["A row with 8 cells instead of 9","Line skipped: \"Expected 9 columns, found 8\""],
["Mark <code>105</code> or <code>-3</code>","Line skipped: \"outside 0–100\""],
["Mark <code>AB</code> (absent)","Line skipped: \"'AB' is not a number\" — stretch: treat AB as 0 and flag it"],
["Duplicate roll number 104","Second row skipped: \"Duplicate roll number 104\""],
["Extra spaces <code>  101 , Aarav Sharma ,10, a ,95…</code>","Parsed; section normalised to A"],
["File saved with a UTF-8 BOM by Excel","Parsed — <code>File.ReadLines</code> detects and strips the BOM"],
["Name containing a comma <code>\"Iyer, Ananya\"</code>","Wrong column count → skipped (known limitation, fixed with CsvHelper in Week 6)"],
["Two students tie for a subject's top score","Both names listed"],
["Head-to-head with section <code>12-Z</code>","\"One of those sections has no students\" (Zip of an empty sequence)"],
["Menu input <code>abc</code>, <code>99</code>, or Ctrl+Z/Ctrl+D","\"Pick a number\" / clean exit on end of input"]])}

<h3>6. README</h3>
{C(r"""
# Grade Analyzer

Micro-project 5 of my .NET full-stack roadmap (Week 5: delegates, lambdas and LINQ).

Reads a class marks CSV and produces school-style reports using LINQ.

## Features
- CSV parsing with per-line validation (column count, numeric marks 0–100, unique roll numbers)
- Grades A1–E by percentage, PASS/FAIL with a pass mark of 33 per subject
- Core reports: class averages, subject toppers (with ties), grade distribution, failures, rank list (1-2-2-4 ranking)
- 10 extra reports: section pivot, best section per subject, top N per section, compartment list,
  strongest/weakest subjects, pass rate per subject, all-rounders, score histogram,
  most consistent students, section head-to-head
- Menu driven by a dictionary of delegates

## CSV format
RollNo,Name,Class,Section,<Subject1>,<Subject2>,...
Subjects are read from the header, so any number of subjects works.

## Run
```bash
dotnet run --project GradeAnalyzer.App                 # uses the bundled students.csv
dotnet run --project GradeAnalyzer.App -- path/to.csv
```

## C# / .NET features used
records, Func/Action, lambdas and closures, local functions, LINQ (GroupBy, ToLookup, GroupJoin,
Zip, Aggregate, MinBy/MaxBy, Chunk-ready), primary constructors, collection expressions
""", "README.md", lang="markdown")}

<h3>7. Git</h3>
{C(r"""
git init
git add .
git commit -m "Grade analyzer: CSV parsing, records, core LINQ reports"
# after today's work
git add .
git commit -m "Add 10 LINQ reports and delegate-driven menu"
git branch -M main
git remote add origin https://github.com/<your-username>/grade-analyzer.git
git push -u origin main
""", lang="bash")}

<h3>8. Week 5 revision checklist</h3>
<ul>
<li>What the compiler generates for a delegate; Target and Method; invocation list</li>
<li>Func / Action / Predicate / Comparison / Converter — and why Predicate isn't a Func</li>
<li>Method group conversion; natural types (C# 10); CS8917</li>
<li>Delegate variance: <code>out</code> = covariant return, <code>in</code> = contravariant parameter, reference types only</li>
<li>Delegates as strategies vs interfaces; callbacks; higher-order functions (Memoize, Retry, Compose)</li>
<li>Lambda forms, discards, explicit return types, C# 12 default parameters</li>
<li>Closures capture variables; display classes; the for-loop gotcha and its fixes</li>
<li>Static lambdas; local functions vs lambdas (table from memory)</li>
<li>Extension method rules; how they compile; why they work on null; fluent builders</li>
<li>Where/Select/OrderBy/ThenBy; First vs Single (+OrDefault); Any/All/Count; Take/Skip/Chunk; DistinctBy/MinBy/MaxBy</li>
<li>Deferred vs immediate; streaming vs buffering; multiple enumeration</li>
<li>GroupBy, Join, GroupJoin left join, SelectMany, Zip, aggregates on empty input, ToDictionary vs ToLookup, set ops and *By</li>
<li>Query syntax clauses and their method equivalents</li>
<li>IEnumerable vs IQueryable; Func vs Expression&lt;Func&gt;; the three EF Core traps</li>
</ul>

<h3>9. Quick quiz — predict the output</h3>
<details><summary>Q1. What prints?</summary>
{C(r"""
var marks = new List<int> { 45, 82, 30 };
var passed = marks.Where(m => m >= 33);
marks.Add(91);
Console.WriteLine(passed.Count());
""")}<b>3.</b> The query is deferred: it runs at Count(), after 91 was added, so 45, 82 and 91 pass.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
var actions = new List<Action>();
for (int i = 0; i < 3; i++) actions.Add(() => Console.Write(i));
foreach (var a in actions) a();
""")}<b>333.</b> All three lambdas capture the same <code>i</code>, which is 3 when they run. Copy to a local inside the loop to get 012.</details>
<details><summary>Q3. Does this compile?</summary>
{C(r"""
Predicate<int> isPass = m => m >= 33;
Func<int, bool> check = isPass;
""")}<b>No.</b> CS0029: Predicate&lt;int&gt; and Func&lt;int, bool&gt; are different delegate types even though their signatures match. Use <code>isPass.Invoke</code> or <code>new Func&lt;int, bool&gt;(isPass)</code>.</details>
<details><summary>Q4. What happens?</summary>
{C(r"""
int[] scores = [];
Console.WriteLine(scores.Sum());
Console.WriteLine(scores.Average());
""")}<b>Prints 0, then throws InvalidOperationException</b> (\"Sequence contains no elements\"). Sum of nothing is 0; the average of nothing is undefined.</details>
<details><summary>Q5. What prints?</summary>
{C(r"""
var names = new[] { "Ravi", "Asha", "Meena", "Anil" };
var q = names.OrderBy(n => n.Length).OrderBy(n => n[0]);
Console.WriteLine(string.Join(",", q));
""")}<b>Asha,Anil,Meena,Ravi.</b> The second OrderBy becomes the primary sort (first letter). Because OrderBy is stable, Asha stays before Anil (their order after the length sort). To sort by length then letter, use <code>OrderBy(n =&gt; n.Length).ThenBy(n =&gt; n[0])</code>.</details>

<div class="note tip"><b>Next week:</b> File I/O and serialization — File and Directory APIs, streams and readers/writers, async file access, paths across Windows/Linux, JSON with System.Text.Json (options, naming policies, custom converters), CSV done properly, and XML basics. You'll make the grade analyzer save reports to JSON and CSV.</div>
''',
iqs=[("Basic","Why build the menu as a Dictionary&lt;int, (string, Action)&gt; instead of a switch?","Each option is data: adding a report means adding one entry, and the loop that prints and dispatches never changes (open/closed principle). It's the delegate-as-strategy pattern from Monday."),
("Basic","Why does report 8 use GroupJoin instead of GroupBy?","GroupBy only produces groups for bands that have students, so empty bands disappear from the histogram. GroupJoin starts from the full list of bands (the outer sequence) and pairs each with its possibly-empty group, so every band shows, including zeros."),
("Intermediate","Report 7 could be written with a nested Average inside All. Why precompute a dictionary?","Inside All, the average would be recomputed for every student and subject: O(students² × subjects). Precomputing section → subject → average once makes each check an O(1) lookup — the same idea as ToLookup instead of a nested Where."),
("Intermediate","How would these reports change if the data lived in SQL Server via EF Core?","Most of them (GroupBy with aggregates, Where, OrderBy, Take, Count) translate to SQL if written against IQueryable, so the database does the work. Computed properties like Student.Total and helpers like ScoreIn wouldn't translate; you'd model marks as a table and express them as Sum/joins in the query, or materialise a filtered set first and finish in memory.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Delegates in depth: Func, Action, Predicate","Delegates in depth","Generic delegates, method groups, variance, strategies, callbacks, higher-order functions.","2 hrs"),
 (2,"TUE","Lambdas, closures and extension methods","Lambdas &amp; closures","Lambda forms, captured variables, the loop gotcha, static lambdas, local functions, fluent APIs.","2 hrs"),
 (3,"WED","LINQ fundamentals","LINQ basics","Where, Select, OrderBy/ThenBy, First vs Single, Any/All, Take/Skip/Chunk, MinBy/MaxBy, deferred execution.","2 hrs"),
 (4,"THU","LINQ: grouping, joins and aggregates","LINQ grouping &amp; joins","GroupBy, Join, left join, SelectMany, Zip, aggregates, ToLookup, set operations.","2 hrs"),
 (5,"FRI","Query syntax, IQueryable and performance","Query syntax &amp; IQueryable","from/where/let/join/into, expression trees, why EF Core needs IQueryable, performance tips.","2 hrs"),
 (6,"SAT","Micro-project 5: Student grade analyzer","Project: grade analyzer","CSV parsing, Student/Mark records, averages, toppers, grade distribution, rank list.","4 hrs"),
 (7,"SUN","10 LINQ reports, README and revision","10 reports &amp; revision","Pivot, histogram, all-rounders, head-to-head, try-to-break, quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week05.html", 5,
      "Week 5 — Delegates, lambdas and LINQ", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 5 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Micro-project 5"],
      "This is the week C# starts to feel expressive. You'll treat methods as values with delegates and lambdas, understand closures well enough to avoid their traps, and learn LINQ — the query toolkit you'll use in nearly every method you write, from in-memory lists to EF Core. The week ends with a student grade analyzer that turns a CSV of marks into school-style reports.",
      cards, days)
print("built")
