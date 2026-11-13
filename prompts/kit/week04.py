import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "List&lt;T&gt;, Dictionary&lt;TKey,TValue&gt; and HashSet&lt;T&gt;",
"Use the three collections you'll write every day, know their costs, and pick the right one for lookups, ordering and uniqueness.",
[("Collection","An object that stores and manages a group of items."),
("Generic collection","A collection typed by a parameter, e.g. <code>List&lt;Order&gt;</code>, giving type safety with no boxing."),
("List&lt;T&gt;","An ordered, index-accessible, resizable array."),
("Capacity","The size of a List's internal array; it doubles when full. Count is how many items are actually stored."),
("Dictionary&lt;TKey,TValue&gt;","A hash table mapping unique keys to values with near-constant-time lookup."),
("KeyValuePair&lt;TKey,TValue&gt;","The element type you get when iterating a dictionary."),
("HashSet&lt;T&gt;","An unordered collection of unique items with fast Contains, plus set operations."),
("Hash table","Structure that uses an item's hash code to jump straight to a bucket instead of scanning."),
("Bucket","A slot in a hash table holding items whose hash codes map to it."),
("Collision","Two different items landing in the same bucket; resolved by comparing with Equals."),
("Big-O","Notation for how cost grows with size: O(1) constant, O(n) linear, O(log n) logarithmic."),
("Comparer","An object that defines equality or order, e.g. <code>StringComparer.OrdinalIgnoreCase</code>.")],
["List = ordered and indexed; Dictionary = lookup by key; HashSet = uniqueness and membership.",
"<code>list.Contains</code> is O(n); <code>set.Contains</code> and <code>dict.ContainsKey</code> are O(1) on average.",
"Use <code>TryGetValue</code> instead of ContainsKey + indexer (one lookup instead of two).",
"The dictionary indexer throws on a missing key when reading, but adds or overwrites when writing.",
"Pass <code>StringComparer.OrdinalIgnoreCase</code> for case-insensitive string keys.",
"Don't add or remove items while looping over a collection with foreach."],
f'''
<h3>1. Why generic collections?</h3>
{C(r"""
int[] fixedSize = new int[3];             // arrays can't grow
var old = new System.Collections.ArrayList { 1, "two", 3.0 };   // object-based: boxing, no type safety
int x = (int)old[1]!;                     // compiles, crashes at runtime: InvalidCastException

var ids = new List<int> { 1, 2, 3 };      // typed, growable, no boxing
// ids.Add("four");                       // ❌ compile error — caught early
""")}

<h3>2. List&lt;T&gt;</h3>
{C(r"""
var cart = new List<string> { "Pen", "Notebook" };
List<string> tags = ["dotnet", "csharp"];          // collection expression (C# 12)

cart.Add("Stapler");                    // end:    O(1) amortised
cart.Insert(0, "Bag");                  // front:  O(n) — shifts everything
cart.AddRange(["Ink", "Ruler"]);
cart.Remove("Ink");                     // first match, O(n)
cart.RemoveAt(0);
cart.RemoveAll(i => i.StartsWith('R')); // removes every match

Console.WriteLine(cart.Count);          // 3
Console.WriteLine(cart[1]);             // Notebook — O(1) by index
Console.WriteLine(cart.Contains("Pen"));// True — O(n) scan
Console.WriteLine(cart.IndexOf("Stapler"));

string? found = cart.Find(i => i.Length > 5);       // first match or null
List<string> longOnes = cart.FindAll(i => i.Length > 3);
cart.Sort();                            // in place, alphabetical
cart.Reverse();

// Capacity vs Count
var big = new List<int>(capacity: 10_000);   // pre-size when you know roughly how many → fewer resizes
""", "ListDemo.cs")}
{warn("Modifying a list inside its own foreach throws <code>InvalidOperationException: Collection was modified</code>. Use <code>RemoveAll</code>, loop backwards with for, or build a new list.", "Gotcha")}

<h3>3. Dictionary&lt;TKey,TValue&gt;</h3>
{C(r"""
var stock = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase)
{
    ["SKU-PEN"] = 120,
    ["SKU-NB"]  = 40
};

stock.Add("SKU-INK", 15);               // throws if the key already exists
stock["SKU-PEN"] = 100;                 // indexer SET: adds or overwrites
bool added = stock.TryAdd("SKU-NB", 99);// false — key exists, nothing changes

// ✓ The right way to read
if (stock.TryGetValue("sku-nb", out int qty))     // case-insensitive thanks to the comparer
    Console.WriteLine($"Notebooks: {qty}");

int ruler = stock.GetValueOrDefault("SKU-RULER");   // 0 when missing
// int bad = stock["SKU-RULER"];                     // ❌ KeyNotFoundException

stock.Remove("SKU-INK");

foreach (var (sku, count) in stock)                 // deconstruct KeyValuePair
    Console.WriteLine($"{sku,-10} {count,5}");

Console.WriteLine(string.Join(", ", stock.Keys));
""", "DictionaryDemo.cs")}
<h4>Classic use: counting and grouping</h4>
{C(r"""
string text = "the quick brown fox jumps over the lazy dog the end";
var wordCounts = new Dictionary<string, int>();

foreach (string word in text.Split(' ', StringSplitOptions.RemoveEmptyEntries))
{
    wordCounts.TryGetValue(word, out int current);   // 0 if missing
    wordCounts[word] = current + 1;
}
Console.WriteLine(wordCounts["the"]);   // 3

// Group orders by customer: Dictionary<string, List<T>>
var ordersByCustomer = new Dictionary<string, List<int>>();
void AddOrder(string customer, int orderId)
{
    if (!ordersByCustomer.TryGetValue(customer, out var list))
    {
        list = [];
        ordersByCustomer[customer] = list;
    }
    list.Add(orderId);
}
""")}

<h3>4. HashSet&lt;T&gt;</h3>
{C(r"""
var emails = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
Console.WriteLine(emails.Add("asha@example.com"));   // True
Console.WriteLine(emails.Add("ASHA@example.com"));   // False — already present
Console.WriteLine(emails.Contains("asha@EXAMPLE.com")); // True, O(1)

// Deduplicate a list in one line
List<int> withDupes = [5, 3, 5, 1, 3];
var unique = new HashSet<int>(withDupes);            // {5, 3, 1}

// Set operations — e.g. compare skills
var required  = new HashSet<string> { "C#", "SQL", "Azure", "Docker" };
var candidate = new HashSet<string> { "C#", "SQL", "React" };

var missing = new HashSet<string>(required);
missing.ExceptWith(candidate);         // Azure, Docker
var overlap = new HashSet<string>(required);
overlap.IntersectWith(candidate);      // C#, SQL
Console.WriteLine(candidate.IsSubsetOf(required));   // False
""", "HashSetDemo.cs")}

<h3>5. How hashing makes lookups fast</h3>
<ol>
<li><code>GetHashCode()</code> turns the key into an int.</li>
<li>The int picks a bucket (roughly <code>hash % bucketCount</code>).</li>
<li>Only items in that bucket are compared with <code>Equals</code>.</li>
<li>With a good hash, buckets hold about one item, so lookup is O(1) regardless of size.</li>
</ol>
<p>This is why last week's Equals/GetHashCode rules matter: a bad or mutable hash code breaks Dictionary and HashSet.</p>

<h3>6. Cost cheat sheet</h3>
{table(["Operation","List&lt;T&gt;","Dictionary","HashSet&lt;T&gt;"],[
["Add","O(1)*","O(1)*","O(1)*"],
["Lookup by index","O(1)","—","—"],
["Lookup by key / Contains","O(n)","O(1)","O(1)"],
["Remove","O(n)","O(1)","O(1)"],
["Keeps insertion order","Yes","Not guaranteed","No"],
["Duplicates","Allowed","Unique keys","Not allowed"]])}
<p class="muted">* amortised: occasionally O(n) when the internal array grows.</p>
''',
["Using <code>List.Contains</code> inside a loop over another list → O(n²). Put one side in a HashSet.",
"Reading <code>dict[key]</code> without checking; use TryGetValue.",
"Calling ContainsKey then the indexer (two lookups).",
"Relying on Dictionary enumeration order.",
"Forgetting a case-insensitive comparer for emails, SKUs or usernames."],
("40 min", ["Read a paragraph and print the 5 most frequent words (ignore case and punctuation) using a Dictionary.",
"Given two lists of 100,000 random ints, find common numbers with nested loops vs a HashSet. Time both with Stopwatch.",
"Build <code>Dictionary&lt;string, List&lt;decimal&gt;&gt;</code> of expenses per category and print totals."]),
[("What does the dictionary indexer do on a missing key?","Reading throws KeyNotFoundException; assigning adds the key."),
("Why is HashSet.Contains faster than List.Contains?","HashSet uses hashing to go straight to one bucket (O(1) average); List compares every element until it finds a match (O(n))."),
("What's the difference between Count and Capacity?","Count is the number of elements stored; Capacity is the size of the internal array, which grows (doubles) when Count reaches it.")],
[("Basic","What is the difference between an array and a List&lt;T&gt;?","An array has a fixed length set at creation. List&lt;T&gt; wraps an array and resizes it automatically, adding methods like Add, Remove, Insert and Find. Both give O(1) index access."),
("Basic","How does a Dictionary work internally?","It's a hash table: the key's GetHashCode selects a bucket, and Equals resolves collisions within it. With well-distributed hashes, add, lookup and remove are O(1) on average."),
("Basic","When would you use a HashSet?","When you need uniqueness or fast membership tests: deduplicating, tracking visited items, checking permissions, or set operations like union and intersection."),
("Intermediate","Why prefer TryGetValue over ContainsKey + indexer?","It does one hash lookup instead of two and avoids the race in concurrent scenarios where the key could be removed between the two calls."),
("Intermediate","What is the time complexity of List.Insert(0, x) and why?","O(n): every existing element must shift one position right in the underlying array. Prefer adding at the end, or use LinkedList/Queue/Deque-like structures when you need fast front insertion."),
("Intermediate","How do you make a Dictionary with case-insensitive string keys?","Pass a comparer to the constructor: <code>new Dictionary&lt;string, T&gt;(StringComparer.OrdinalIgnoreCase)</code>. The comparer supplies both GetHashCode and Equals for keys.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Queue, Stack, LinkedList, SortedDictionary and choosing the right collection",
"Recognise FIFO, LIFO, priority and sorted problems, and reach for the matching collection instead of forcing everything into a List.",
[("Queue&lt;T&gt;","First-in, first-out (FIFO) collection: Enqueue at the back, Dequeue from the front."),
("Stack&lt;T&gt;","Last-in, first-out (LIFO) collection: Push on top, Pop from the top."),
("PriorityQueue&lt;TElement,TPriority&gt;",".NET 6+ queue that always dequeues the item with the lowest priority value."),
("Peek","Look at the next item without removing it."),
("LinkedList&lt;T&gt;","Doubly linked list of nodes; O(1) insert/remove when you hold the node, no index access."),
("LinkedListNode&lt;T&gt;","A node with Value, Next and Previous."),
("SortedDictionary&lt;K,V&gt;","Key-value pairs kept sorted by key, backed by a red-black tree (O(log n))."),
("SortedList&lt;K,V&gt;","Sorted key-value pairs in two arrays; less memory, slower inserts, index access."),
("SortedSet&lt;T&gt;","Unique items kept in sorted order, with range queries like GetViewBetween."),
("Deque","Double-ended queue (add/remove at both ends); .NET has no built-in one, LinkedList can serve."),
("FIFO / LIFO","Processing order: first in first out (queues) vs last in first out (stacks).")],
["Queue for jobs processed in arrival order; Stack for undo, backtracking and nested structures.",
"PriorityQueue when \"most urgent first\" matters more than arrival order.",
"Use the Try* methods (TryDequeue, TryPop, TryPeek) to avoid exceptions on empty collections.",
"LinkedList only wins when you keep node references and insert/remove in the middle often.",
"Need sorted keys? SortedDictionary for frequent inserts, SortedList for mostly-read data.",
"When unsure, start with List or Dictionary and change only if profiling shows a need."],
f'''
<h3>1. Queue&lt;T&gt; — first come, first served</h3>
{C(r"""
public record SupportTicket(int Id, string Customer, string Issue);

var tickets = new Queue<SupportTicket>();
tickets.Enqueue(new(1, "Asha",  "Can't log in"));
tickets.Enqueue(new(2, "Ravi",  "Refund status"));
tickets.Enqueue(new(3, "Meena", "Wrong item delivered"));

Console.WriteLine(tickets.Peek().Customer);      // Asha — next up, not removed
while (tickets.TryDequeue(out var t))            // safe: stops when empty
    Console.WriteLine($"Handling #{t.Id} for {t.Customer}: {t.Issue}");

// tickets.Dequeue();                            // ❌ InvalidOperationException: Queue empty
""", "SupportQueue.cs")}

<h3>2. PriorityQueue — most urgent first</h3>
{C(r"""
// Lower priority number = served first
var triage = new PriorityQueue<string, int>();
triage.Enqueue("Sprained ankle", 3);
triage.Enqueue("Chest pain", 1);
triage.Enqueue("Fever", 2);
triage.Enqueue("Cardiac arrest", 0);

while (triage.TryDequeue(out string? patient, out int priority))
    Console.WriteLine($"P{priority}: {patient}");
// P0: Cardiac arrest
// P1: Chest pain
// P2: Fever
// P3: Sprained ankle
""", "Triage.cs")}
{warn("PriorityQueue is not stable: two items with the same priority may come out in any order. Add a tie-breaker (e.g. a tuple priority <code>(severity, arrivalNumber)</code>) if order matters.", "Note")}

<h3>3. Stack&lt;T&gt; — last in, first out</h3>
{C(r"""
// Undo for a text editor
var history = new Stack<string>();
string doc = "";

void Type(string text) { history.Push(doc); doc += text; }
void Undo() { if (history.TryPop(out var previous)) doc = previous; }

Type("Hello");
Type(", world");
Type("!!!");
Undo();
Console.WriteLine(doc);     // Hello, world

// Bracket matching — classic interview problem
static bool IsBalanced(string s)
{
    var open = new Stack<char>();
    foreach (char c in s)
    {
        if (c is '(' or '[' or '{') { open.Push(c); continue; }
        if (c is ')' or ']' or '}')
        {
            if (!open.TryPop(out char top)) return false;
            if ((top, c) is not (('(', ')') or ('[', ']') or ('{', '}'))) return false;
        }
    }
    return open.Count == 0;
}

Console.WriteLine(IsBalanced("var x = list[(a + b)];"));   // True
Console.WriteLine(IsBalanced("if (x > 0] {"));             // False
""", "StackDemo.cs")}

<h3>4. LinkedList&lt;T&gt;</h3>
{C(r"""
var playlist = new LinkedList<string>();
var first = playlist.AddLast("Intro");
var chorus = playlist.AddLast("Chorus");
playlist.AddLast("Outro");

playlist.AddAfter(first, "Verse 1");        // O(1) — we hold the node
playlist.AddBefore(chorus, "Pre-chorus");
playlist.Remove(chorus);                     // O(1) with the node

for (var node = playlist.First; node is not null; node = node.Next)
    Console.Write($"{node.Value} → ");       // Intro → Verse 1 → Pre-chorus → Outro →

// playlist[2]                               // ❌ no indexer: reaching the nth item is O(n)
""", "Playlist.cs")}
<p>In practice LinkedList is rare: List is usually faster because its items sit next to each other in memory (CPU cache friendly). It's the building block for an <b>LRU cache</b> (Dictionary + LinkedList), a common interview design question.</p>

<h3>5. Sorted collections</h3>
{C(r"""
// Leaderboard sorted by score (key)
var leaderboard = new SortedDictionary<int, string>(Comparer<int>.Create((a, b) => b.CompareTo(a)))   // descending
{
    [870] = "Neha",
    [990] = "Rohit",
    [915] = "Imran"
};
foreach (var (score, name) in leaderboard)
    Console.WriteLine($"{score} {name}");       // 990 Rohit, 915 Imran, 870 Neha

// SortedSet with range queries
var prices = new SortedSet<decimal> { 499, 1299, 89, 2499, 799 };
Console.WriteLine(prices.Min);                   // 89
Console.WriteLine(string.Join(", ", prices.GetViewBetween(500, 2000)));   // 799, 1299
""")}
{table(["","SortedDictionary","SortedList","Dictionary + sort when needed"],[
["Insert","O(log n)","O(n)","O(1)"],
["Lookup","O(log n)","O(log n)","O(1)"],
["Memory","Higher (tree nodes)","Lower (arrays)","Medium"],
["Index access","No","Yes (Keys[i])","No"],
["Best when","Frequent inserts, always sorted","Built once, read many times","Sorting is occasional"]])}

<h3>6. Choosing the right collection</h3>
{table(["You need…","Use"],[
["Ordered items, access by position","<code>List&lt;T&gt;</code>"],
["Fixed-size, performance-critical buffer","<code>T[]</code>"],
["Look up by a key","<code>Dictionary&lt;K,V&gt;</code>"],
["Uniqueness / fast \"have I seen this?\"","<code>HashSet&lt;T&gt;</code>"],
["Process in arrival order","<code>Queue&lt;T&gt;</code>"],
["Most urgent first","<code>PriorityQueue&lt;T,P&gt;</code>"],
["Undo, backtracking, nested parsing","<code>Stack&lt;T&gt;</code>"],
["Always sorted by key, frequent changes","<code>SortedDictionary&lt;K,V&gt;</code>"],
["Sorted unique values + range queries","<code>SortedSet&lt;T&gt;</code>"],
["Many middle inserts with node references","<code>LinkedList&lt;T&gt;</code>"],
["Shared across threads","<code>ConcurrentDictionary</code>, <code>ConcurrentQueue</code> (Week 7)"],
["Never changes after startup, read constantly","<code>FrozenDictionary</code> / <code>FrozenSet</code> (Friday)"]])}
''',
["Using List with <code>RemoveAt(0)</code> as a queue (O(n) each time).",
"Calling Dequeue/Pop/Peek without checking Count; use the Try* methods.",
"Choosing LinkedList \"for performance\" without measuring.",
"Expecting PriorityQueue to preserve arrival order for equal priorities.",
"Using SortedList for data that's inserted constantly."],
("40 min", ["Simulate a bank counter: customers arrive into a Queue, two tellers serve them, print who served whom.",
"Implement browser Back/Forward with two Stacks.",
"Use a PriorityQueue to schedule tasks by (priority, dueDate) and print the order."]),
[("What does Peek do?","Returns the next item (front of a queue, top of a stack) without removing it; throws if empty, so prefer TryPeek."),
("When is LinkedList better than List?","When you frequently insert or remove in the middle and already hold the node reference, making it O(1). Otherwise List is usually faster."),
("What does PriorityQueue dequeue first?","The element with the smallest priority according to the priority comparer (a min-heap by default).")],
[("Basic","What is the difference between a Queue and a Stack?","A Queue is FIFO: the first item added is the first removed (Enqueue/Dequeue). A Stack is LIFO: the last item added is the first removed (Push/Pop). Queues model waiting lines; stacks model undo history and nested calls."),
("Basic","Give real-world uses for Stack&lt;T&gt;.","Undo/redo, browser back navigation, matching brackets or HTML tags, depth-first search, evaluating expressions, and the call stack itself."),
("Basic","What is a PriorityQueue and how is it implemented?","A queue that dequeues by priority rather than arrival order. .NET's PriorityQueue is an array-backed min-heap (quaternary heap) with O(log n) enqueue/dequeue."),
("Intermediate","SortedDictionary vs SortedList vs Dictionary?","Dictionary: unordered, O(1) average. SortedDictionary: red-black tree, sorted, O(log n) insert/lookup. SortedList: sorted arrays, O(log n) lookup but O(n) insert, less memory and index access. Pick by insert frequency and whether you need order."),
("Intermediate","How would you design an LRU cache in C#?","Combine Dictionary&lt;K, LinkedListNode&lt;(K, V)&gt;&gt; for O(1) lookup with a LinkedList ordered by recent use. On get, move the node to the front; on put, add to the front and, if over capacity, remove the last node and its dictionary entry."),
("Intermediate","Why can List outperform LinkedList even for some inserts?","List stores elements contiguously, so it's CPU-cache friendly and memory-light. LinkedList allocates a node per item scattered around the heap, causing cache misses and GC pressure; finding the insertion point is O(n) anyway unless you hold the node.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Generics: classes, methods and constraints",
"Write your own reusable, type-safe generic types and methods, and restrict type parameters with constraints so the compiler can help you.",
[("Generics","Writing types and methods with type parameters, filled in by the caller: <code>List&lt;T&gt;</code>."),
("Type parameter","The placeholder, conventionally <code>T</code>, <code>TKey</code>, <code>TResult</code>."),
("Type argument","The real type supplied: in <code>List&lt;Order&gt;</code>, Order is the type argument."),
("Open vs closed type","<code>List&lt;T&gt;</code> is open; <code>List&lt;int&gt;</code> is closed (all arguments supplied)."),
("Generic method","A method with its own type parameters: <code>T Max&lt;T&gt;(T a, T b)</code>."),
("Type inference","The compiler working out type arguments from the method arguments."),
("Constraint","A <code>where</code> clause limiting what types are allowed and unlocking their members."),
("default(T)","The default value of T: null for references, zero for value types."),
("Reification","In .NET, generic types exist at runtime with their real type arguments (unlike Java's erasure)."),
("Covariance (out)","Allows <code>IEnumerable&lt;Derived&gt;</code> to be used as <code>IEnumerable&lt;Base&gt;</code>."),
("Contravariance (in)","Allows <code>IComparer&lt;Base&gt;</code> to be used as <code>IComparer&lt;Derived&gt;</code>."),
("Invariance","Neither: <code>List&lt;Derived&gt;</code> is not a <code>List&lt;Base&gt;</code>.")],
["Generics give you reuse without giving up type safety or performance.",
"Without constraints you can only use members of <code>object</code> on T.",
"Add the minimum constraints needed; each one narrows who can use your code.",
"Static fields are per closed type: <code>Cache&lt;int&gt;</code> and <code>Cache&lt;string&gt;</code> don't share them.",
"Generic methods usually don't need explicit type arguments; inference handles it.",
"List&lt;Derived&gt; isn't List&lt;Base&gt;, but IEnumerable&lt;Derived&gt; is IEnumerable&lt;Base&gt;."],
f'''
<h3>1. The problem generics solve</h3>
{C(r"""
// Without generics: one class per type, or `object` and casting
public class IntBox    { public int Value { get; set; } }
public class StringBox { public string Value { get; set; } = ""; }
public class ObjectBox { public object? Value { get; set; } }   // boxing + casts + runtime errors

// With generics: one definition, any type, fully typed
public class Box<T>
{
    public T Value { get; set; }
    public Box(T value) => Value = value;
}

var price = new Box<decimal>(499m);
decimal p = price.Value;          // no cast, no boxing
var name = new Box<string>("Pen");
""")}

<h3>2. Generic classes you'll actually write</h3>
{C(r"""
// A result type (you wrote a non-generic flavour in Week 2)
public readonly record struct Result<T>(bool IsSuccess, T? Value, string? Error)
{
    public static Result<T> Ok(T value) => new(true, value, null);
    public static Result<T> Fail(string error) => new(false, default, error);

    public TOut Match<TOut>(Func<T, TOut> onOk, Func<string, TOut> onFail) =>
        IsSuccess ? onOk(Value!) : onFail(Error!);
}

// Paging for APIs (Week 18)
public record PagedResult<T>(IReadOnlyList<T> Items, int Page, int PageSize, int TotalCount)
{
    public int TotalPages => (int)Math.Ceiling(TotalCount / (double)PageSize);
    public bool HasNext => Page < TotalPages;
}

// Two type parameters
public record Pair<TFirst, TSecond>(TFirst First, TSecond Second);
""", "GenericTypes.cs")}
{C(r"""
Result<decimal> r = Result<decimal>.Ok(1180m);
string msg = r.Match(v => $"Total {v:N2}", err => $"Error: {err}");

var page = new PagedResult<string>(["a", "b"], Page: 1, PageSize: 2, TotalCount: 5);
Console.WriteLine($"{page.TotalPages} pages, next? {page.HasNext}");   // 3 pages, next? True
""")}

<h3>3. Generic methods and inference</h3>
{C(r"""
public static class Util
{
    public static void Swap<T>(ref T a, ref T b) => (a, b) = (b, a);

    public static T FirstOr<T>(IEnumerable<T> items, T fallback)
    {
        foreach (var item in items) return item;
        return fallback;
    }

    public static Dictionary<TKey, List<T>> GroupBy<T, TKey>(IEnumerable<T> items, Func<T, TKey> keyOf)
        where TKey : notnull
    {
        var groups = new Dictionary<TKey, List<T>>();
        foreach (var item in items)
        {
            var key = keyOf(item);
            if (!groups.TryGetValue(key, out var list)) groups[key] = list = [];
            list.Add(item);
        }
        return groups;
    }
}

int x = 1, y = 2;
Util.Swap(ref x, ref y);                         // T inferred as int
string first = Util.FirstOr(new string[0], "none");
var byLength = Util.GroupBy(["C#", "SQL", "Go", "Rust"], w => w.Length);   // {2: [C#, Go], 3: [SQL], 4: [Rust]}
""", "Util.cs")}

<h3>4. Constraints</h3>
<p>Without constraints, T could be anything, so the compiler only lets you use <code>object</code> members. Constraints promise more, unlocking more.</p>
{C(r"""
// ❌ Won't compile: the compiler doesn't know T can be compared
// static T Max<T>(T a, T b) => a > b ? a : b;

// ✓ Constrain T to things that know how to compare themselves
static T Max<T>(T a, T b) where T : IComparable<T> => a.CompareTo(b) >= 0 ? a : b;

Console.WriteLine(Max(3, 7));                 // 7
Console.WriteLine(Max("apple", "mango"));     // mango
Console.WriteLine(Max(new DateOnly(2026, 1, 1), new DateOnly(2025, 6, 1)));
""")}
{table(["Constraint","Means","Unlocks"],[
["<code>where T : class</code>","Reference type","T can be null; use <code>as</code>"],
["<code>where T : class?</code>","Nullable reference type allowed",""],
["<code>where T : struct</code>","Non-nullable value type","<code>T?</code> means Nullable&lt;T&gt;"],
["<code>where T : notnull</code>","Non-nullable type (ref or value)","Safe dictionary keys"],
["<code>where T : unmanaged</code>","Struct with no references","Pointers, stackalloc, raw memory"],
["<code>where T : new()</code>","Has a public parameterless constructor","<code>new T()</code>"],
["<code>where T : BaseClass</code>","Is or derives from BaseClass","BaseClass members"],
["<code>where T : IInterface</code>","Implements the interface","Interface members"],
["<code>where T : U</code>","T is or derives from another type parameter U",""]])}
{C(r"""
public interface IEntity { int Id { get; } }

// Several constraints: class first, new() last
public class Repository<T> where T : class, IEntity, new()
{
    private readonly Dictionary<int, T> _items = new();

    public T Create() => new T();                     // needs new()
    public void Save(T item) => _items[item.Id] = item; // needs IEntity
    public T? Find(int id) => _items.GetValueOrDefault(id); // T? is null for missing, thanks to `class`
}
""", "Repository.cs")}

<h3>5. default(T), static members and runtime types</h3>
{C(r"""
static T GetOrDefault<T>(T[] items, int index) =>
    index >= 0 && index < items.Length ? items[index] : default!;   // null or 0

Console.WriteLine(GetOrDefault(new[] { 1, 2 }, 5));      // 0
Console.WriteLine(GetOrDefault(new[] { "a" }, 5) ?? "null");

public class Counter<T>
{
    public static int Instances;                  // one per CLOSED type
    public Counter() => Instances++;
}
new Counter<int>(); new Counter<int>(); new Counter<string>();
Console.WriteLine(Counter<int>.Instances);        // 2
Console.WriteLine(Counter<string>.Instances);     // 1

Console.WriteLine(typeof(List<int>));             // System.Collections.Generic.List`1[System.Int32]
""")}

<h3>6. Variance (in / out)</h3>
{C(r"""
IEnumerable<string> names = ["Asha", "Ravi"];
IEnumerable<object> objects = names;          // ✓ covariance: IEnumerable<out T>

List<string> nameList = ["Asha"];
// List<object> objList = nameList;           // ❌ invariant: you could then Add(42) to a List<string>

IComparer<object> byHash = Comparer<object>.Create((a, b) => a.GetHashCode().CompareTo(b.GetHashCode()));
IComparer<string> forStrings = byHash;        // ✓ contravariance: IComparer<in T>

Func<object> makeObj = () => "hi";
Func<string> makeStr = () => "hi";
makeObj = makeStr;                            // ✓ Func<out TResult>
""")}
<p>Rule of thumb: <code>out T</code> means T only comes <i>out</i> (returned), so a more derived T is safe. <code>in T</code> means T only goes <i>in</i> (parameters), so a more general T is safe.</p>
''',
["Using <code>object</code> parameters where a generic method would keep type safety.",
"Over-constraining (e.g. adding <code>new()</code> you never use).",
"Expecting <code>List&lt;Dog&gt;</code> to be assignable to <code>List&lt;Animal&gt;</code>.",
"Forgetting that static fields aren't shared across different closed generic types.",
"Writing <code>T? Find()</code> without a <code>class</code> or <code>struct</code> constraint and being surprised it doesn't return null for value types."],
("40 min", ["Write a generic <code>Stack&lt;T&gt;</code> of your own (array-backed, grows when full) with Push, Pop, Peek, TryPop and Count.",
"Write <code>static T MaxBy&lt;T, TKey&gt;(IEnumerable&lt;T&gt; items, Func&lt;T, TKey&gt; key) where TKey : IComparable&lt;TKey&gt;</code> and find the most expensive product.",
"Create <code>Cache&lt;TKey, TValue&gt;</code> with a fixed capacity that evicts the oldest entry (use a Dictionary and a Queue)."]),
[("Why can't you use &gt; on an unconstrained T?","The compiler doesn't know T supports comparison. Constrain to IComparable&lt;T&gt; and use CompareTo, or (in .NET 7+) to IComparisonOperators."),
("What does the new() constraint allow?","Calling <code>new T()</code> inside the generic code, because T must have a public parameterless constructor."),
("Are generics in C# erased at runtime like Java?","No. .NET keeps full type information at runtime; value-type instantiations get specialised native code, so List&lt;int&gt; has no boxing.")],
[("Basic","What are generics and what are their benefits?","Generics let you define classes, interfaces and methods with type parameters. Benefits: compile-time type safety, code reuse across types, and performance (no boxing or casting for value types)."),
("Basic","What are generic constraints? Name some.","where clauses restricting type arguments: class, struct, notnull, unmanaged, new(), a base class, an interface, or another type parameter. They let the generic code use the members those constraints guarantee."),
("Basic","What is default(T)?","The default value for whatever T is: null for reference types, 0/false/zeroed struct for value types. Useful as a 'not found' return or initial value."),
("Intermediate","Explain covariance and contravariance with examples.","Covariance (out T) lets a generic type with a derived argument be used where a base argument is expected: IEnumerable&lt;string&gt; as IEnumerable&lt;object&gt;. Contravariance (in T) is the reverse for inputs: IComparer&lt;object&gt; as IComparer&lt;string&gt;. Only interfaces and delegates support variance, and List&lt;T&gt; is invariant."),
("Intermediate","How does .NET implement generics at runtime?","Generic types are reified. For reference-type arguments the JIT shares one native code instance (all references are pointer-sized); for each value-type argument it generates specialised code, so List&lt;int&gt; and List&lt;double&gt; are each optimised without boxing."),
("Intermediate","Why are static fields in a generic class not shared across type arguments?","Each closed constructed type (Counter&lt;int&gt;, Counter&lt;string&gt;) is a distinct type at runtime with its own static storage. This is sometimes used deliberately as a per-type cache.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "IEnumerable, ICollection, IList and yield return",
"Understand the collection interfaces, how foreach really works, and write lazy sequences with yield return — the foundation of LINQ next week.",
[("IEnumerable&lt;T&gt;","The most basic sequence: something you can iterate once with foreach. Exposes GetEnumerator()."),
("IEnumerator&lt;T&gt;","The cursor over a sequence: MoveNext(), Current, Dispose()."),
("IReadOnlyCollection&lt;T&gt;","An enumerable that also knows its Count."),
("ICollection&lt;T&gt;","Adds Count, Add, Remove, Contains, Clear, CopyTo."),
("IReadOnlyList&lt;T&gt;","Count plus read-only index access."),
("IList&lt;T&gt;","ICollection plus index get/set, Insert, RemoveAt, IndexOf."),
("Iterator","A method or property using <code>yield return</code> to produce a sequence lazily."),
("yield return","Returns the next element and pauses the method until the caller asks for another."),
("yield break","Ends the sequence early."),
("Lazy / deferred execution","Work happens only when the sequence is enumerated, one element at a time."),
("Multiple enumeration","Iterating the same lazy sequence twice, repeating all its work (and side effects)."),
("Materialise","Forcing a lazy sequence to run and store results, e.g. ToList() or ToArray().")],
["foreach works on anything with GetEnumerator(); IEnumerable&lt;T&gt; is the standard way to offer it.",
"Accept the most general type you need (IEnumerable&lt;T&gt;), return the most useful read-only type (IReadOnlyList&lt;T&gt;).",
"yield return turns a method into a lazy state machine; nothing runs until you iterate.",
"Lazy sequences can be infinite; take only what you need.",
"Argument validation in an iterator is deferred too — split into a wrapper method.",
"Call ToList() once if you'll iterate a lazy sequence more than once."],
f'''
<h3>1. The collection interface hierarchy</h3>
<pre class="mermaid">
flowchart TB
  IE["IEnumerable&lt;T&gt;<br/>foreach"] --> IRC["IReadOnlyCollection&lt;T&gt;<br/>+ Count"]
  IE --> IC["ICollection&lt;T&gt;<br/>+ Count, Add, Remove, Contains"]
  IRC --> IRL["IReadOnlyList&lt;T&gt;<br/>+ this[i] get"]
  IC --> IL["IList&lt;T&gt;<br/>+ this[i] get/set, Insert, RemoveAt"]
  IC --> ISet["ISet&lt;T&gt;<br/>+ set operations"]
  IC --> ID["IDictionary&lt;K,V&gt;"]
  IL --> L["List&lt;T&gt;, T[]"]
  IRL --> L
</pre>
{table(["Interface","Can iterate","Count","Index","Modify"],[
["<code>IEnumerable&lt;T&gt;</code>","✓","","",""],
["<code>IReadOnlyCollection&lt;T&gt;</code>","✓","✓","",""],
["<code>IReadOnlyList&lt;T&gt;</code>","✓","✓","read",""],
["<code>ICollection&lt;T&gt;</code>","✓","✓","","Add/Remove"],
["<code>IList&lt;T&gt;</code>","✓","✓","read/write","Add/Remove/Insert"]])}
<h4>Choosing parameter and return types</h4>
{C(r"""
// Parameters: ask for the LEAST you need, so callers can pass anything
public decimal Total(IEnumerable<OrderLine> lines) { /* ... */ return 0; }

// Returns: give the MOST useful read-only view, so callers can Count and index without copying
public IReadOnlyList<Order> RecentOrders() => _orders.TakeLast(10).ToList();
""")}

<h3>2. How foreach really works</h3>
{C(r"""
var cities = new List<string> { "Pune", "Kochi", "Indore" };

foreach (var city in cities) Console.WriteLine(city);

// …is compiled roughly into:
using (IEnumerator<string> e = cities.GetEnumerator())
{
    while (e.MoveNext())
    {
        var city = e.Current;
        Console.WriteLine(city);
    }
}
""")}

<h3>3. Implementing IEnumerable&lt;T&gt; yourself</h3>
{C(r"""
using System.Collections;

public class DateSpan : IEnumerable<DateOnly>
{
    private readonly DateOnly _start, _end;
    public DateSpan(DateOnly start, DateOnly end)
    {
        if (end < start) throw new ArgumentException("End before start");
        (_start, _end) = (start, end);
    }

    // yield return builds the enumerator for us
    public IEnumerator<DateOnly> GetEnumerator()
    {
        for (var d = _start; d <= _end; d = d.AddDays(1))
            yield return d;
    }

    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();   // non-generic version, required
}

var week = new DateSpan(new DateOnly(2026, 11, 9), new DateOnly(2026, 11, 15));
foreach (var d in week)
    if (d.DayOfWeek is not (DayOfWeek.Saturday or DayOfWeek.Sunday))
        Console.Write($"{d:ddd dd} ");   // Mon 09 Tue 10 Wed 11 Thu 12 Fri 13
""", "DateSpan.cs")}

<h3>4. yield return: lazy sequences</h3>
{C(r"""
static IEnumerable<int> CountTo(int n)
{
    Console.WriteLine("  [start]");
    for (int i = 1; i <= n; i++)
    {
        Console.WriteLine($"  [yield {i}]");
        yield return i;                   // pause here, hand i to the caller
    }
    Console.WriteLine("  [end]");
}

var seq = CountTo(3);                     // NOTHING printed yet — deferred
Console.WriteLine("Before loop");
foreach (int x in seq)
    Console.WriteLine($"got {x}");

// Before loop
//   [start]
//   [yield 1]
// got 1
//   [yield 2]
// got 2
//   [yield 3]
// got 3
//   [end]
""", "YieldDemo.cs")}
<h4>Infinite sequences and yield break</h4>
{C(r"""
static IEnumerable<long> Fibonacci()
{
    long a = 0, b = 1;
    while (true)                          // infinite — safe because it's lazy
    {
        yield return a;
        (a, b) = (b, a + b);
    }
}

foreach (long f in Fibonacci())
{
    if (f > 100) break;
    Console.Write($"{f} ");               // 0 1 1 2 3 5 8 13 21 34 55 89
}

static IEnumerable<string> ReadUntilBlank(IEnumerable<string> lines)
{
    foreach (var line in lines)
    {
        if (string.IsNullOrWhiteSpace(line)) yield break;   // stop the sequence
        yield return line.Trim();
    }
}
""")}
<h4>Streaming a large file</h4>
{C(r"""
// Reads one line at a time — memory stays flat even for a 5 GB log
static IEnumerable<string> ErrorLines(string path)
{
    foreach (string line in File.ReadLines(path))     // File.ReadLines is itself lazy
        if (line.Contains("ERROR", StringComparison.Ordinal))
            yield return line;
}
""")}

<h3>5. Iterator pitfalls</h3>
{C(r"""
// ❌ Validation is deferred: no exception until someone iterates
static IEnumerable<int> Range(int start, int count)
{
    if (count < 0) throw new ArgumentOutOfRangeException(nameof(count));
    for (int i = 0; i < count; i++) yield return start + i;
}
var r = Range(1, -5);        // no error here!
// foreach (var i in r) {}   // error only now, far from the cause

// ✓ Split: eager validation + private lazy iterator
static IEnumerable<int> SafeRange(int start, int count)
{
    ArgumentOutOfRangeException.ThrowIfNegative(count);   // runs immediately
    return Iterate();

    IEnumerable<int> Iterate()
    {
        for (int i = 0; i < count; i++) yield return start + i;
    }
}

// ❌ Multiple enumeration repeats the work
IEnumerable<string> errors = ErrorLines("app.log");
int count = errors.Count();          // reads the whole file
var first = errors.First();          // reads it AGAIN

// ✓ Materialise once
List<string> errorList = ErrorLines("app.log").ToList();
""")}
{tip("Next week's LINQ methods (<code>Where</code>, <code>Select</code>, <code>Take</code>) are mostly yield-based iterators like these. Understanding today makes deferred execution obvious.")}
''',
["Returning <code>List&lt;T&gt;</code> from public methods so callers can modify your internal data.",
"Accepting <code>List&lt;T&gt;</code> parameters when <code>IEnumerable&lt;T&gt;</code> would do.",
"Enumerating a lazy sequence several times without realising it re-runs.",
"Putting validation inside iterator methods.",
"Calling <code>ToList()</code> on an infinite sequence."],
("40 min", ["Write <code>IEnumerable&lt;DateOnly&gt; WorkingDays(DateOnly from, DateOnly to, ISet&lt;DateOnly&gt; holidays)</code> with yield.",
"Write <code>IEnumerable&lt;T[]&gt; Chunk&lt;T&gt;(IEnumerable&lt;T&gt; source, int size)</code> that yields batches (validate size eagerly).",
"Write a lazy <code>Primes()</code> sequence and print the first 20 primes."]),
[("What must a type have for foreach to work?","A public GetEnumerator() method returning something with MoveNext() and Current. Implementing IEnumerable&lt;T&gt; is the standard way."),
("When does the code in a yield method run?","Only when the caller starts enumerating, and only up to the next yield each time MoveNext() is called."),
("Why return IReadOnlyList&lt;T&gt; rather than IEnumerable&lt;T&gt;?","It tells callers the data is already materialised, gives them Count and indexing, and avoids accidental multiple enumeration.")],
[("Basic","What is the difference between IEnumerable and IList?","IEnumerable only supports forward iteration. IList adds Count, index-based get/set, Add, Insert, Remove and RemoveAt. Accept IEnumerable when you only need to loop; use IList when you need positional modification."),
("Basic","What does yield return do?","It makes the method an iterator: each yield return hands one element to the caller and pauses; execution resumes from that point on the next MoveNext. The compiler generates a state machine class implementing IEnumerable/IEnumerator."),
("Basic","What is deferred execution?","The sequence's work isn't done when it's defined, only when it's enumerated. Results reflect the source data at enumeration time, and each enumeration redoes the work."),
("Intermediate","What is the multiple-enumeration problem?","Enumerating a deferred sequence more than once repeats its work — re-reading files, re-querying databases, re-running side effects — and may return different results. Materialise with ToList() when you need it more than once."),
("Intermediate","Why does argument validation in an iterator behave unexpectedly?","Because the whole method body, including validation, only runs at the first MoveNext. Exceptions surface far from the call site. Fix by validating in a non-iterator wrapper that returns a local iterator function."),
("Intermediate","IEnumerable vs IQueryable?","IEnumerable executes in memory with delegates (LINQ to Objects). IQueryable builds expression trees that a provider (like EF Core) translates to SQL and runs in the database. You'll study this in Weeks 5 and 15.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "IComparable, IComparer, IEquatable and immutable/frozen collections",
"Control how your types sort and compare, plug custom comparers into collections, and pick read-only, immutable or frozen collections for safety and speed.",
[("IComparable&lt;T&gt;","A type's natural order, implemented by the type itself via CompareTo."),
("IComparer&lt;T&gt;","An external ordering strategy; lets the same type sort many ways."),
("Comparer&lt;T&gt;.Create","Builds an IComparer from a lambda."),
("IEquatable&lt;T&gt;","A type's strongly typed equality."),
("IEqualityComparer&lt;T&gt;","External equality strategy (Equals + GetHashCode) for dictionaries, sets and Distinct."),
("StringComparer","Built-in comparers for strings: Ordinal, OrdinalIgnoreCase, CurrentCulture…"),
("Stable sort","Equal elements keep their original order. List.Sort is unstable; LINQ OrderBy is stable."),
("Read-only collection","A view that hides mutating methods, but the underlying data can still change."),
("Immutable collection","System.Collections.Immutable: can never change; 'changes' return a new collection sharing structure."),
("Builder","A mutable helper (ImmutableList.CreateBuilder) for efficiently constructing an immutable collection."),
("Frozen collection",".NET 8 FrozenDictionary/FrozenSet: built once, optimised for very fast reads."),
("Ordinal comparison","Compares raw character codes; fast and culture-independent.")],
["IComparable = the one natural order; IComparer = any other order you need.",
"CompareTo returns negative (before), zero (same), positive (after).",
"Use <code>Comparer&lt;T&gt;.Create</code> or LINQ OrderBy/ThenBy instead of writing comparer classes by hand.",
"IEqualityComparer lets a Dictionary or HashSet use your definition of 'same' without changing the type.",
"Read-only ≠ immutable: a ReadOnlyCollection wraps a list someone else can still change.",
"FrozenDictionary for lookup tables that never change after startup."],
f'''
<h3>1. IComparable&lt;T&gt; — natural order</h3>
{C(r"""
public record Version(int Major, int Minor, int Patch) : IComparable<Version>
{
    public int CompareTo(Version? other)
    {
        if (other is null) return 1;
        int c = Major.CompareTo(other.Major);
        if (c != 0) return c;
        c = Minor.CompareTo(other.Minor);
        return c != 0 ? c : Patch.CompareTo(other.Patch);
    }

    public static Version Parse(string s)
    {
        var p = s.Split('.').Select(int.Parse).ToArray();
        return new(p[0], p[1], p[2]);
    }

    public override string ToString() => $"{Major}.{Minor}.{Patch}";
}

var versions = new List<Version> { Version.Parse("8.0.11"), Version.Parse("9.0.0"), Version.Parse("8.0.2") };
versions.Sort();
Console.WriteLine(string.Join(", ", versions));   // 8.0.2, 8.0.11, 9.0.0 (string sort would give 8.0.11 first)
""", "Version.cs")}

<h3>2. IComparer&lt;T&gt; — many orders for one type</h3>
{C(r"""
public record Product(string Sku, string Name, decimal Price, int Rating);

var products = new List<Product>
{
    new("P1", "Mouse", 799m, 4),
    new("P2", "Keyboard", 1499m, 5),
    new("P3", "Headset", 1499m, 3),
    new("P4", "Webcam", 2499m, 4)
};

// A comparer class
public sealed class PriceThenRatingDesc : IComparer<Product>
{
    public int Compare(Product? x, Product? y)
    {
        if (x is null || y is null) return Comparer<Product?>.Default.Compare(x, y);
        int byPrice = x.Price.CompareTo(y.Price);
        return byPrice != 0 ? byPrice : y.Rating.CompareTo(x.Rating);   // higher rating first
    }
}
products.Sort(new PriceThenRatingDesc());

// Or a lambda comparer
products.Sort(Comparer<Product>.Create((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase)));

// Or LINQ (stable, returns a new sequence) — usually the most readable
var sorted = products.OrderBy(p => p.Price).ThenByDescending(p => p.Rating).ToList();

// Comparers plug into sorted collections too
var bySku = new SortedSet<Product>(Comparer<Product>.Create((a, b) => string.CompareOrdinal(a.Sku, b.Sku)));
""", "Comparers.cs")}

<h3>3. IEqualityComparer&lt;T&gt; — your own definition of "same"</h3>
<p>Gmail ignores dots and anything after <code>+</code> in the local part. To treat <code>s.nayak+jobs@gmail.com</code> and <code>snayak@gmail.com</code> as one user, give the set a comparer instead of changing <code>string</code>.</p>
{C(r"""
public sealed class GmailAddressComparer : IEqualityComparer<string>
{
    public bool Equals(string? x, string? y) =>
        string.Equals(Normalize(x), Normalize(y), StringComparison.Ordinal);

    public int GetHashCode(string obj) => Normalize(obj)?.GetHashCode() ?? 0;

    private static string? Normalize(string? email)
    {
        if (email is null) return null;
        var parts = email.Trim().ToLowerInvariant().Split('@');
        if (parts is not [var local, "gmail.com"]) return email.Trim().ToLowerInvariant();
        local = local.Split('+')[0].Replace(".", "");
        return $"{local}@gmail.com";
    }
}

var signups = new HashSet<string>(new GmailAddressComparer())
{
    "snayak@gmail.com",
    "s.nayak+jobs@gmail.com",     // same person → not added
    "S.Nayak@Gmail.com"           // same person → not added
};
Console.WriteLine(signups.Count);   // 1

var distinct = new[] { "a.b@gmail.com", "ab@gmail.com" }.Distinct(new GmailAddressComparer()).Count();   // 1
""", "GmailAddressComparer.cs")}
{tip("Equality comparers must obey the same rule as GetHashCode on types: if Equals says two values match, GetHashCode must return the same number for both.")}

<h3>4. Read-only vs immutable vs frozen</h3>
{C(r"""
using System.Collections.Frozen;
using System.Collections.Immutable;

var source = new List<string> { "IN", "US" };

// Read-only VIEW: can't modify through it, but it reflects changes to `source`
IReadOnlyList<string> view = source.AsReadOnly();
source.Add("UK");
Console.WriteLine(view.Count);              // 3 — changed underneath you

// Immutable: truly can't change; "modifying" returns a new collection
ImmutableList<string> imm = ["IN", "US"];
ImmutableList<string> imm2 = imm.Add("UK");
Console.WriteLine($"{imm.Count} {imm2.Count}");   // 2 3

// Build large immutable collections efficiently
var builder = ImmutableDictionary.CreateBuilder<string, decimal>();
builder.Add("GST", 0.18m);
builder.Add("TDS", 0.10m);
ImmutableDictionary<string, decimal> rates = builder.ToImmutable();

// Frozen (.NET 8): slower to create, fastest to read
FrozenDictionary<string, string> stateCodes = new Dictionary<string, string>
{
    ["KA"] = "Karnataka", ["MH"] = "Maharashtra", ["TN"] = "Tamil Nadu", ["DL"] = "Delhi"
}.ToFrozenDictionary(StringComparer.OrdinalIgnoreCase);

FrozenSet<string> blockedPins = new[] { "000000", "999999" }.ToFrozenSet();

Console.WriteLine(stateCodes["ka"]);         // Karnataka
""", "CollectionsDemo.cs")}
{table(["","ReadOnlyCollection / IReadOnlyList","ImmutableList / ImmutableDictionary","FrozenDictionary / FrozenSet"],[
["Can the data change?","Yes, via the original","Never","Never"],
["\"Add\" returns","Not available","A new collection","Not available"],
["Read speed","Same as the list","Slower (tree-based)","Fastest"],
["Creation cost","Almost free","Medium","Highest (optimises layout)"],
["Thread safe for reads","Only if nobody writes the source","Yes","Yes"],
["Use for","Exposing internal lists safely","Shared state that evolves by snapshots","Lookup tables built once at startup"]])}

<h3>5. Putting it together: a product catalogue lookup</h3>
{C(r"""
public sealed class Catalog
{
    private readonly FrozenDictionary<string, Product> _bySku;
    private readonly IReadOnlyList<Product> _byPrice;

    public Catalog(IEnumerable<Product> products)
    {
        var list = products.ToList();
        _bySku = list.ToFrozenDictionary(p => p.Sku, StringComparer.OrdinalIgnoreCase);
        _byPrice = list.OrderBy(p => p.Price).ThenBy(p => p.Name).ToList().AsReadOnly();
    }

    public Product? Find(string sku) => _bySku.GetValueOrDefault(sku);
    public IReadOnlyList<Product> CheapestFirst => _byPrice;
}
""", "Catalog.cs")}
''',
["CompareTo that isn't consistent (A &lt; B and B &lt; A both true) — Sort can throw or loop.",
"Sorting strings with culture-sensitive comparison for keys/IDs; use Ordinal.",
"Thinking <code>AsReadOnly()</code> makes data immutable.",
"Using ImmutableList for hot, frequently read data when a frozen or plain list would be faster.",
"An IEqualityComparer whose GetHashCode disagrees with its Equals."],
("40 min", ["Make <code>Employee</code> implement <code>IComparable&lt;Employee&gt;</code> by Id, then sort by department then salary descending with a comparer.",
"Write a case- and whitespace-insensitive <code>IEqualityComparer&lt;string&gt;</code> for city names and use it in a HashSet.",
"Build a <code>FrozenDictionary</code> of PIN-code prefixes to states and look up 10 PIN codes."]),
[("What should CompareTo return?","A negative number if this comes before other, zero if they're equal in order, positive if it comes after."),
("Is List.Sort stable?","No (it uses introsort). Enumerable.OrderBy is stable."),
("When would you choose a FrozenDictionary?","For data created once (often at startup) and read very frequently, like configuration maps, country codes or routing tables.")],
[("Basic","What is the difference between IComparable and IComparer?","IComparable&lt;T&gt; is implemented by the type itself to define its single natural order (CompareTo). IComparer&lt;T&gt; is a separate object defining an ordering, so you can sort the same type in many ways without changing it."),
("Basic","What is IEqualityComparer used for?","To supply custom equality (Equals + GetHashCode) to hash-based collections and LINQ methods like Distinct, without modifying the element type — e.g. case-insensitive strings or normalised emails."),
("Basic","Read-only vs immutable collection?","A read-only collection only prevents modification through that reference; the underlying collection may still change. An immutable collection can never change after creation; operations return new instances."),
("Intermediate","What are frozen collections and when do they help?",".NET 8's FrozenDictionary and FrozenSet analyse the data at creation to choose an optimal lookup strategy, making reads faster than Dictionary at the cost of slower construction. Ideal for static lookup tables read on hot paths."),
("Intermediate","How do immutable collections stay efficient?","They use persistent data structures (balanced trees) that share most of their structure between versions, so adding an item creates O(log n) new nodes rather than copying everything. Builders allow efficient batch construction."),
("Intermediate","Why prefer ordinal string comparison for identifiers?","Ordinal compares raw char values: it's faster, predictable and culture-independent. Culture-aware comparison can give different results on different machines (e.g. Turkish i), which breaks keys and sorting of codes.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Refactor the library project around a generic repository",
"Replace the Week 2 catalog with a generic repository, add indexes with Dictionary and HashSet, and add reservations with Queue — without changing the business rules. Budget: about 4 hours.",
[("Repository","An abstraction that stores and retrieves entities like an in-memory collection, hiding where the data really lives."),
("Generic repository","One repository implementation reused for every entity type: <code>IRepository&lt;T&gt;</code>."),
("Entity","An object with an identity (Id) that persists over time."),
("Index","An extra lookup structure (e.g. Dictionary by ISBN) that avoids scanning all items."),
("Reservation queue","A FIFO line of members waiting for an item.")],
["One generic InMemoryRepository&lt;T&gt; replaces separate item and member storage.",
"Dictionary&lt;int, T&gt; gives O(1) lookup by Id instead of scanning a list.",
"HashSet guards uniqueness of ISBNs and emails in O(1).",
"Queue&lt;int&gt; per item holds reservations in arrival order.",
"Refactoring means behaviour stays the same; re-run last week's 'try to break it' table to prove it."],
f'''
<h3>What changes</h3>
{table(["Week 2","Week 4"],[
["<code>ICatalog</code> with item- and member-specific methods","<code>IRepository&lt;T&gt;</code> for any entity"],
["<code>List&lt;LibraryItem&gt;</code> + <code>FirstOrDefault</code> scans","<code>Dictionary&lt;int, T&gt;</code> lookups"],
["ISBN/email checks by scanning","<code>HashSet&lt;string&gt;</code> indexes"],
["Loans in a list scanned for each check","<code>Dictionary&lt;int, List&lt;Loan&gt;&gt;</code> by member + <code>Dictionary&lt;int, Loan&gt;</code> by item"],
["No reservations","<code>Dictionary&lt;int, Queue&lt;int&gt;&gt;</code> per item"]])}

<h3>Step 1 — IEntity and IRepository&lt;T&gt;</h3>
{C(r"""
namespace Library.Core.Interfaces;

public interface IEntity
{
    int Id { get; }
}
""", "Library.Core/Interfaces/IEntity.cs")}
{C(r"""
namespace Library.Core.Interfaces;

public interface IRepository<T> where T : class, IEntity
{
    int Count { get; }
    void Add(T entity);
    T? GetById(int id);
    bool Remove(int id);
    IReadOnlyList<T> GetAll();
    IReadOnlyList<T> Find(Func<T, bool> predicate);     // Func: a delegate (Week 3, Day 5)
}
""", "Library.Core/Interfaces/IRepository.cs")}
<p>Make <code>LibraryItem</code>, <code>Member</code> and <code>Loan</code> implement <code>IEntity</code>. Items and members already have <code>Id</code>; give <code>Loan</code> one with a static counter.</p>
{C(r"""
public abstract class LibraryItem : ISearchable, IEntity { /* unchanged */ }
public class Member : ISearchable, IEntity { /* unchanged */ }

public class Loan : IEntity
{
    private static int _nextId = 1;
    public int Id { get; } = _nextId++;
    /* rest unchanged */
}
""")}

<h3>Step 2 — InMemoryRepository&lt;T&gt;</h3>
{C(r"""
using Library.Core.Interfaces;

namespace Library.Core.Services;

public class InMemoryRepository<T> : IRepository<T> where T : class, IEntity
{
    private readonly Dictionary<int, T> _store = new();

    public int Count => _store.Count;

    public virtual void Add(T entity)
    {
        ArgumentNullException.ThrowIfNull(entity);
        if (!_store.TryAdd(entity.Id, entity))
            throw new InvalidOperationException($"{typeof(T).Name} with id {entity.Id} already exists");
    }

    public T? GetById(int id) => _store.GetValueOrDefault(id);

    public virtual bool Remove(int id) => _store.Remove(id);

    public IReadOnlyList<T> GetAll() => _store.Values.ToList();

    public IReadOnlyList<T> Find(Func<T, bool> predicate)
    {
        var results = new List<T>();
        foreach (var item in _store.Values)
            if (predicate(item)) results.Add(item);
        return results;
    }
}
""", "Library.Core/Services/InMemoryRepository.cs")}

<h3>Step 3 — Specialised repositories with unique indexes</h3>
<p>Inherit the generic behaviour and add a HashSet index for the field that must be unique.</p>
{C(r"""
using Library.Core.Models;

namespace Library.Core.Services;

public class ItemRepository : InMemoryRepository<LibraryItem>
{
    private readonly HashSet<string> _isbns = new(StringComparer.Ordinal);

    public override void Add(LibraryItem item)
    {
        if (item is Book book && !_isbns.Add(book.Isbn))
            throw new InvalidOperationException($"A book with ISBN {book.Isbn} already exists");
        base.Add(item);
    }

    public override bool Remove(int id)
    {
        if (GetById(id) is Book book) _isbns.Remove(book.Isbn);
        return base.Remove(id);
    }

    public IReadOnlyList<T> OfKind<T>() where T : LibraryItem => Find(i => i is T).Cast<T>().ToList();
}

public class MemberRepository : InMemoryRepository<Member>
{
    private readonly Dictionary<string, Member> _byEmail = new(StringComparer.OrdinalIgnoreCase);

    public override void Add(Member member)
    {
        if (!_byEmail.TryAdd(member.Email, member))
            throw new InvalidOperationException($"{member.Email} is already registered");
        base.Add(member);
    }

    public Member? GetByEmail(string email) => _byEmail.GetValueOrDefault(email.Trim());
}
""", "Library.Core/Services/Repositories.cs")}

<h3>Step 4 — LibraryService with indexed loans and reservations</h3>
{C(r"""
using Library.Core.Interfaces;
using Library.Core.Models;

namespace Library.Core.Services;

public class LibraryService(ItemRepository items, MemberRepository members, IClock clock)
{
    private readonly InMemoryRepository<Loan> _loans = new();
    private readonly Dictionary<int, Loan> _openLoanByItem = new();             // itemId → open loan
    private readonly Dictionary<int, List<Loan>> _openLoansByMember = new();    // memberId → open loans
    private readonly Dictionary<int, Queue<int>> _reservations = new();         // itemId → waiting memberIds

    public IReadOnlyList<Loan> OpenLoans => _openLoanByItem.Values.ToList();
    public IReadOnlyList<Loan> Overdue => _openLoanByItem.Values.Where(l => l.DaysOverdue(clock.Today) > 0).ToList();

    public Result<Loan> Borrow(int memberId, int itemId)
    {
        if (members.GetById(memberId) is not { } member) return Result<Loan>.Fail($"No member with id {memberId}");
        if (items.GetById(itemId) is not { } item)       return Result<Loan>.Fail($"No item with id {itemId}");
        if (_openLoanByItem.ContainsKey(itemId))         return Result<Loan>.Fail($"'{item.Title}' is already on loan");

        // Reserved? Only the member at the front of the queue may take it
        if (_reservations.TryGetValue(itemId, out var queue) && queue.TryPeek(out int nextInLine) && nextInLine != memberId)
            return Result<Loan>.Fail($"'{item.Title}' is reserved for member {nextInLine}");

        var memberLoans = OpenLoansOf(memberId);
        if (memberLoans.Count >= Member.MaxLoans)
            return Result<Loan>.Fail($"{member.Name} already has {Member.MaxLoans} items out");
        if (memberLoans.Any(l => l.DaysOverdue(clock.Today) > 0))
            return Result<Loan>.Fail($"{member.Name} has an overdue item; return it first");

        var loan = new Loan(item, member, clock.Today);
        _loans.Add(loan);
        _openLoanByItem[itemId] = loan;
        memberLoans.Add(loan);
        item.IsAvailable = false;
        queue?.TryDequeue(out _);                       // their reservation is fulfilled
        return Result<Loan>.Ok(loan);
    }

    public Result<decimal> Return(int itemId)
    {
        if (!_openLoanByItem.Remove(itemId, out var loan))
            return Result<decimal>.Fail($"Item {itemId} isn't on loan");

        decimal fee = loan.Close(clock.Today);
        OpenLoansOf(loan.Member.Id).Remove(loan);
        loan.Item.IsAvailable = true;
        return Result<decimal>.Ok(fee);
    }

    public Result<int> Reserve(int memberId, int itemId)
    {
        if (members.GetById(memberId) is null) return Result<int>.Fail($"No member with id {memberId}");
        if (items.GetById(itemId) is not { } item) return Result<int>.Fail($"No item with id {itemId}");
        if (item.IsAvailable) return Result<int>.Fail($"'{item.Title}' is available — borrow it instead");

        if (!_reservations.TryGetValue(itemId, out var queue))
            _reservations[itemId] = queue = new Queue<int>();
        if (queue.Contains(memberId)) return Result<int>.Fail("You're already in the queue");

        queue.Enqueue(memberId);
        return Result<int>.Ok(queue.Count);            // position in line
    }

    public IReadOnlyList<ISearchable> Search(string term)
    {
        if (string.IsNullOrWhiteSpace(term)) return [];
        var hits = new List<ISearchable>();
        hits.AddRange(items.Find(i => i.Matches(term)));
        hits.AddRange(members.Find(m => m.Matches(term)));
        return hits;
    }

    private List<Loan> OpenLoansOf(int memberId)
    {
        if (!_openLoansByMember.TryGetValue(memberId, out var list))
            _openLoansByMember[memberId] = list = [];
        return list;
    }
}
""", "Library.Core/Services/LibraryService.cs")}
<p><code>is not {{ }} member</code> is a property pattern that checks for non-null and assigns in one step (Week 3, Day 2).</p>

<h3>Step 5 — Wire it up</h3>
{C(r"""
var items = new ItemRepository();
var members = new MemberRepository();
SeedData.Load(items, members);              // update SeedData to take the two repositories
var clock = new ManualClock(DateOnly.FromDateTime(DateTime.Today));
var library = new LibraryService(items, members, clock);

// New menu option:
// case 10: Reserve(); break;

void Reserve()
{
    int memberId = ConsoleInput.ReadInt("Member id: ", 1, int.MaxValue);
    int itemId   = ConsoleInput.ReadInt("Item id: ", 1, int.MaxValue);
    var r = library.Reserve(memberId, itemId);
    Console.WriteLine(r.Success ? $"  ✓ You're number {r.Value} in line" : $"  ✗ {r.Error}");
}

// Listing books only, sorted by title, using the generic helper and a comparer
foreach (var b in items.OfKind<Book>().OrderBy(b => b.Title, StringComparer.OrdinalIgnoreCase))
    Console.WriteLine($"  {b}");
""", "Library.App/Program.cs (changes)")}

<h3>Step 6 — Regression check</h3>
<p>Re-run every row of the Week 2 Sunday table; results must be identical. Then test the new feature:</p>
{table(["Scenario","Expected"],[
["Member 1001 borrows item 1","✓ loan created"],
["Member 1002 reserves item 1","✓ number 1 in line"],
["Member 1002 reserves item 1 again","\"You're already in the queue\""],
["Member 1001 returns item 1; member 1003 tries to borrow it","\"reserved for member 1002\""],
["Member 1002 borrows item 1","✓ and the reservation queue is now empty"],
["Reserve an item that's available","\"borrow it instead\""]])}

<h3>Stretch goals</h3>
<ul>
<li>Add <code>PagedResult&lt;T&gt; GetPage(int page, int size)</code> to the repository and page through items 2 at a time.</li>
<li>Add an undo for the last borrow/return using a <code>Stack</code> of actions.</li>
<li>Write the regression table as a small console \"test runner\" that prints PASS/FAIL (you'll replace it with xUnit in Week 10).</li>
</ul>
''',
iqs=[("Basic","What is the Repository pattern?","An abstraction over data storage that exposes collection-like operations (Add, GetById, Find, Remove) for entities, so business logic doesn't depend on whether data lives in memory, SQL Server or an API."),
("Basic","Why constrain IRepository&lt;T&gt; with where T : class, IEntity?","IEntity guarantees an Id the repository can key on; class allows returning null for 'not found' (T?) and matches how entities are modelled."),
("Intermediate","What are the criticisms of a generic repository over EF Core?","DbContext/DbSet is already a repository and unit of work, so a thin generic wrapper often adds little, hides useful features (Include, projections, IQueryable) and leaks abstractions. Many teams prefer specific repositories or query objects per use case."),
("Intermediate","Why keep secondary indexes like _openLoanByItem, and what's the risk?","They turn O(n) scans into O(1) lookups. The risk is consistency: every add/remove must update all indexes, so mutations should be centralised in one place — exactly what a database does for you with indexes and transactions.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Revise Weeks 1–4 and write notes in your own words",
"Consolidate the first month: check what you can explain without notes, fill gaps, and write your own cheat sheets.",
[("Active recall","Testing yourself from memory instead of re-reading; far more effective for retention."),
("Feynman technique","Explain a topic in plain words as if teaching a beginner; gaps show up where you get stuck."),
("Spaced repetition","Reviewing material at increasing intervals (1 day, 3 days, 1 week, 1 month).")],
["Close the notes before answering anything below.",
"If you can't explain something in two sentences, re-read only that section.",
"Write your cheat sheets by hand or in your own markdown repo; don't copy these pages.",
"Mark each topic green / amber / red and revisit reds next weekend."],
f'''
<h3>1. How to spend today (≈4 hours)</h3>
{table(["Time","Activity"],[
["45 min","Blank-page recall: for each week, write everything you remember on one page"],
["45 min","Compare with the notes; mark each checklist item green/amber/red"],
["60 min","Re-study reds; type out one code example per red topic"],
["45 min","Mixed quiz and mock interview below (answer aloud, record yourself)"],
["30 min","Write your own cheat sheet for collections and push it to a <code>dotnet-notes</code> repo"],
["15 min","Finish Saturday's refactor, update the library README, push"]])}

<h3>2. One-month checklist</h3>
<h4>Week 1 — C# basics</h4>
<ul><li>SDK vs runtime; CLR, IL, JIT</li><li>Value vs reference types; decimal vs double</li><li>Parse / TryParse / Convert; switch expressions</li><li>String immutability and StringBuilder; arrays, ranges</li><li>ref / out / in; nullable types and ?. ?? ??=</li></ul>
<h4>Week 2 — OOP</h4>
<ul><li>Properties vs fields; init, required, primary constructors</li><li>Encapsulation; access modifiers; static members</li><li>Inheritance, constructor order, virtual/override vs new, sealed</li><li>Abstract classes, polymorphism, Template Method</li><li>Interfaces, DI by hand, interface vs abstract class</li></ul>
<h4>Week 3 — Modern C#</h4>
<ul><li>struct vs class vs record vs record struct vs tuple</li><li>Pattern kinds; tuple-switch state machines; list patterns</li><li>Enums and flags; Equals/GetHashCode contract; boxing</li><li>Exceptions: order, filters, throw vs throw ex, custom hierarchy</li><li>Delegates, Func/Action, events and leaks</li></ul>
<h4>Week 4 — Collections and generics</h4>
<ul><li>List / Dictionary / HashSet costs and when to use each</li><li>Queue / Stack / PriorityQueue / LinkedList / sorted collections</li><li>Generic classes, methods, constraints, variance</li><li>IEnumerable vs ICollection vs IList; yield and deferred execution</li><li>IComparable vs IComparer; IEqualityComparer; read-only vs immutable vs frozen</li></ul>

<h3>3. Collections cheat sheet</h3>
{table(["Collection","Order","Duplicates","Add","Find","Remove","Use when"],[
["<code>T[]</code>","Index","Yes","—","O(n) / O(1) index","—","Fixed size"],
["<code>List&lt;T&gt;</code>","Insertion","Yes","O(1)*","O(n) / O(1) index","O(n)","Default ordered list"],
["<code>Dictionary&lt;K,V&gt;</code>","None","Keys unique","O(1)","O(1) by key","O(1)","Lookup by key"],
["<code>HashSet&lt;T&gt;</code>","None","No","O(1)","O(1)","O(1)","Uniqueness, membership"],
["<code>Queue&lt;T&gt;</code>","FIFO","Yes","O(1)","—","O(1) front","Arrival order"],
["<code>Stack&lt;T&gt;</code>","LIFO","Yes","O(1)","—","O(1) top","Undo, nesting"],
["<code>PriorityQueue</code>","Priority","Yes","O(log n)","—","O(log n)","Most urgent first"],
["<code>SortedDictionary</code>","Key","Keys unique","O(log n)","O(log n)","O(log n)","Always sorted"],
["<code>LinkedList&lt;T&gt;</code>","Insertion","Yes","O(1) with node","O(n)","O(1) with node","Middle inserts"],
["<code>FrozenDictionary</code>","None","Keys unique","—","Fastest","—","Static lookups"]])}

<h3>4. Mixed quiz — predict the output</h3>
<details><summary>Q1. What prints?</summary>
{C(r"""
var d = new Dictionary<string, int>();
d["a"] = 1; d["a"] = 2;
Console.WriteLine(d.Count + d["a"]);
""")}<b>3.</b> The indexer overwrites, so Count is 1 and the value is 2.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
IEnumerable<int> Nums() { Console.Write("A"); yield return 1; Console.Write("B"); yield return 2; }
var n = Nums();
Console.Write("C");
foreach (var x in n) Console.Write(x);
""")}<b>CA1B2.</b> Nothing runs until enumeration starts.</details>
<details><summary>Q3. What prints?</summary>
{C(r"""
var s = new Stack<int>([1, 2, 3]);
var q = new Queue<int>([1, 2, 3]);
Console.WriteLine($"{s.Pop()}{q.Dequeue()}");
""")}<b>31.</b> The stack's top is the last pushed (3); the queue's front is the first enqueued (1).</details>
<details><summary>Q4. Does this compile?</summary>
{C(r"""
List<object> items = new List<string> { "a" };
""")}<b>No.</b> List&lt;T&gt; is invariant. <code>IEnumerable&lt;object&gt; items = new List&lt;string&gt;()</code> would compile (covariance).</details>
<details><summary>Q5. What prints?</summary>
{C(r"""
var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "Pune", "PUNE", "pune", "Goa" };
Console.WriteLine(set.Count);
""")}<b>2.</b> The comparer treats the three Pune spellings as one.</details>
<details><summary>Q6. What prints?</summary>
{C(r"""
struct P { public int X; }
var list = new List<P> { new P { X = 1 } };
var p = list[0]; p.X = 9;
Console.WriteLine(list[0].X);
""")}<b>1.</b> The indexer returns a copy of the struct; changing the copy doesn't change the list.</details>
<details><summary>Q7. What prints?</summary>
{C(r"""
record R(int A);
var set = new HashSet<R> { new R(1), new R(1) };
Console.WriteLine(set.Count);
""")}<b>1.</b> Records have value equality and matching hash codes.</details>
<details><summary>Q8. What prints?</summary>
{C(r"""
try { int[] a = new int[2]; a[2] = 1; }
catch (IndexOutOfRangeException) { Console.Write("I"); }
catch (Exception) { Console.Write("E"); }
finally { Console.Write("F"); }
""")}<b>IF.</b> The specific catch handles it, then finally runs.</details>

<h3>5. Mock interview (answer aloud, 2 minutes each)</h3>
<ol>
<li>Walk me through what happens from <code>dotnet run</code> to your Main method executing.</li>
<li>Explain value vs reference types, and where boxing happens.</li>
<li>Interface or abstract class for a payment gateway integration? Why?</li>
<li>How would you make a <code>Money</code> type safe to use as a dictionary key?</li>
<li>When would you throw an exception vs return a result object?</li>
<li>You need to check if 1 million incoming order IDs were already processed. What collection and why?</li>
<li>What is deferred execution and how can it bite you?</li>
<li>Design an LRU cache with O(1) get and put.</li>
</ol>

<h3>6. Write your own notes</h3>
<p>Create a <code>dotnet-notes</code> repo with one markdown file per week. For each topic write: a one-line definition, one example from your own projects (bank, library), one gotcha. Writing it yourself is what makes it stick.</p>
{C(r"""
mkdir dotnet-notes && cd dotnet-notes
git init
printf "# Week 4 — Collections\n\n## Dictionary\n- What: ...\n- My example: ...\n- Gotcha: ...\n" > week04.md
git add . && git commit -m "Week 4 notes" && git push
""", lang="bash")}

<div class="note tip"><b>Next week:</b> Delegates in depth, lambdas, closures and LINQ — Where, Select, OrderBy, GroupBy, Join, SelectMany, aggregates, and IEnumerable vs IQueryable. Micro-project 5 is a student grade analyser over CSV data.</div>
''',
iqs=[("Basic","You need to check whether 1 million order IDs were already processed. What do you use?","A HashSet&lt;long&gt; (or HashSet&lt;Guid&gt;): O(1) Contains and Add, and Add returns false for duplicates so check-and-insert is one call. For persistence across restarts, a unique index in the database."),
("Intermediate","Design an LRU cache with O(1) get and put.","Dictionary from key to LinkedListNode, plus a LinkedList ordered by recency. Get: look up the node, move it to the front, return the value. Put: update or add at the front; if over capacity, remove the last node and its dictionary entry. Both are O(1)."),
("Intermediate","How would you make Money safe as a dictionary key?","Make it immutable (readonly record struct Money(decimal Amount, string Currency)), so Equals and GetHashCode are value-based and can't change after insertion. Normalise the currency code (upper case) in the constructor."),
("Intermediate","Interface or abstract class for payment gateways?","An interface (IPaymentGateway) as the contract consumers depend on and tests mock, optionally with an abstract base class implementing the shared steps (logging, retries, validation) via Template Method for concrete gateways to inherit.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","List, Dictionary and HashSet","List · Dictionary · HashSet","Everyday collections, TryGetValue, comparers, set operations, Big-O.","2 hrs"),
 (2,"TUE","Queue, Stack, LinkedList, sorted collections","Queue · Stack · Sorted","FIFO, LIFO, PriorityQueue, LRU idea, choosing the right collection.","2 hrs"),
 (3,"WED","Generics and constraints","Generics","Generic classes and methods, constraints, default(T), variance.","2 hrs"),
 (4,"THU","IEnumerable, IList and yield","IEnumerable &amp; yield","Collection interfaces, how foreach works, iterators, deferred execution.","2 hrs"),
 (5,"FRI","Comparers, equality and frozen collections","Comparers &amp; frozen","IComparable vs IComparer, IEqualityComparer, immutable vs frozen.","2 hrs"),
 (6,"SAT","Library refactor: generic repository","Project: repository","IRepository&lt;T&gt;, indexes, reservations queue, regression check.","4 hrs"),
 (7,"SUN","Revise Weeks 1–4","Month-1 revision","Checklist, cheat sheet, mixed quiz, mock interview, your own notes.","4 hrs"),
]
build("/home/claude/build/week03.html", "/home/claude/build/week04.html", 4,
      "Week 4 — Collections and generics", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 4 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Library refactor"],
      "Almost every method you write will take or return a collection. This week you'll learn which collection fits which problem and what it costs, how to write your own generic types, how foreach and yield really work, and how to control sorting and equality. Sunday wraps up the first month with a full revision.",
      cards, days)
print("built")
