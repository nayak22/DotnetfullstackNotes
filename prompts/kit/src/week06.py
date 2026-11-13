import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "System.IO: files, directories, paths, streams and encodings",
"Read and write files safely on Windows, Linux and macOS: build paths correctly, pick between one-shot helpers and streams, stream big files line by line, use the async APIs, and avoid encoding surprises with ₹ and Indian-language text.",
[("System.IO","The namespace for files, directories, paths and streams. It's included by implicit usings in console projects."),
("Path","Static helpers that build and take apart path strings (Combine, Join, GetFileName, GetExtension…). They don't touch the disk."),
("File / Directory","Static one-call helpers that do touch the disk: read, write, copy, move, delete, enumerate."),
("FileInfo / DirectoryInfo","Object versions of File/Directory. They cache metadata like Length and LastWriteTime until you call Refresh()."),
("Absolute vs relative path","An absolute path starts at a root (<code>C:\\</code> or <code>/</code>). A relative path is resolved against the <b>current working directory</b>."),
("Current directory","The folder the process was started from (<code>Directory.GetCurrentDirectory()</code>). This is not always the folder the .dll is in."),
("Stream","A sequence of bytes you read or write in order. <code>FileStream</code>, <code>MemoryStream</code> and network streams all derive from <code>Stream</code>."),
("StreamReader / StreamWriter","Wrappers that turn a byte stream into text (and back) using an encoding."),
("Buffer","An in-memory block that collects small reads and writes into fewer, larger disk operations. Data sits in it until it's flushed."),
("Flush","Push buffered data down to the next layer. Dispose flushes automatically."),
("FileMode / FileAccess / FileShare","Open options: create or open the file, read or write it, and what other processes may do with it while you have it open."),
("Encoding","The rules that turn characters into bytes. UTF-8 is the .NET default; ₹ takes 3 bytes in UTF-8."),
("BOM","Byte Order Mark: optional bytes at the start of a file (EF BB BF for UTF-8) that mark its encoding."),
("Lazy reading","<code>File.ReadLines</code> returns an IEnumerable that reads one line at a time as you loop (Week 4's deferred execution).")],
["Build paths with <code>Path.Combine</code> or <code>Path.Join</code>. Never join them with <code>\"\\\\\"</code> or <code>\"/\"</code> by hand.",
"<code>File.ReadAllText</code>/<code>WriteAllText</code> are fine for small files. Use <code>File.ReadLines</code> or a stream for big ones.",
"<code>File.WriteAllText</code> overwrites the file without asking. Use <code>AppendAllText</code> to add to it.",
"Always dispose streams (<code>using</code>). An undisposed writer can lose its buffered data and keep the file locked.",
"Default text encoding is UTF-8 without a BOM. <code>Encoding.UTF8</code> writes a BOM, but <code>new UTF8Encoding(false)</code> doesn't.",
"A relative path depends on where the user ran the app from. For app data, use a known folder."],
f'''
<h3>1. Paths that work on every OS</h3>
<p>Windows separates folders with <code>\\</code>, Linux and macOS with <code>/</code>. If you hard-code either one, your app breaks on the other OS. The <code>Path</code> class uses the right separator for you. It only works with strings and never checks whether the file exists.</p>
{C(r"""
string dataDir = Path.Combine("data", "2026", "invoices");   // data/2026/invoices (Linux) or data\2026\invoices (Windows)
string file = Path.Combine(dataDir, "INV-1001.json");

Console.WriteLine(Path.GetFileName(file));                   // INV-1001.json
Console.WriteLine(Path.GetFileNameWithoutExtension(file));   // INV-1001
Console.WriteLine(Path.GetExtension(file));                  // .json
Console.WriteLine(Path.GetDirectoryName(file));              // data/2026/invoices
Console.WriteLine(Path.ChangeExtension(file, ".pdf"));       // data/2026/invoices/INV-1001.pdf
Console.WriteLine(Path.GetFullPath(file));                   // /home/priya/app/data/2026/invoices/INV-1001.json (depends on current directory)
Console.WriteLine(Path.DirectorySeparatorChar);              // '/' on Linux/macOS, '\' on Windows
Console.WriteLine(Path.IsPathRooted("/etc/hosts"));          // True
""", "Paths.cs")}
{warn("<code>Path.Combine(\"uploads\", \"/etc/passwd\")</code> returns <code>/etc/passwd</code>. If any later argument is rooted, Combine throws away everything before it. With user input that's a path-traversal hole. <code>Path.Join</code> just joins the parts (<code>uploads/etc/passwd</code>). For names that users type, also strip folders with <code>Path.GetFileName(input)</code> and check that the final <code>GetFullPath</code> still starts with your base folder.", "Security")}
{C(r"""
static string SafeUploadPath(string baseFolder, string userFileName)
{
    string fullBase = Path.GetFullPath(baseFolder);
    string name = Path.GetFileName(userFileName);               // "../../secrets.txt" → "secrets.txt"
    if (name.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
        throw new ArgumentException($"Invalid file name: {userFileName}");

    string full = Path.GetFullPath(Path.Join(fullBase, name));
    if (!full.StartsWith(fullBase + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        throw new UnauthorizedAccessException("Path escapes the upload folder");
    return full;
}
""")}
<h4>Where should your app keep its files?</h4>
{C(r"""
Console.WriteLine(Directory.GetCurrentDirectory());   // where the user ran the command from
Console.WriteLine(AppContext.BaseDirectory);          // where the .dll lives, e.g. .../bin/Debug/net8.0/

string appData = Path.Combine(
    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ExpenseTracker");
// Windows: C:\Users\<you>\AppData\Local\ExpenseTracker
// Linux:   ~/.local/share/ExpenseTracker

string temp = Path.GetTempPath();                     // OS temp folder
""")}
{table(["Folder","Use it for","Watch out"],[
["Current directory","Files the user named on the command line","Changes depending on where the app was launched"],
["<code>AppContext.BaseDirectory</code>","Read-only files shipped with the app (appsettings.json)","Usually not writable once installed (Program Files)"],
["<code>LocalApplicationData</code>","The app's own data: databases, JSON stores, caches","Per user; create the subfolder yourself"],
["<code>Path.GetTempPath()</code>","Short-lived scratch files","The OS may clean it up at any time"]])}

<h3>2. File and Directory: one-call helpers</h3>
{C(r"""
string folder = Path.Combine(Path.GetTempPath(), "gst-demo");
Directory.CreateDirectory(folder);                       // creates missing parents too; no error if it already exists

string path = Path.Combine(folder, "customers.txt");
File.WriteAllText(path, "Asha Rao,Pune,411001\n");       // creates or OVERWRITES
File.AppendAllText(path, "Ravi Kumar,Chennai,600001\n");
File.AppendAllLines(path, ["Meena Iyer,Kochi,682001"]);  // adds a line ending after each line

string all = File.ReadAllText(path);                     // whole file as one string
string[] lines = File.ReadAllLines(path);
Console.WriteLine(lines.Length);                         // 3
Console.WriteLine(File.Exists(path));                    // True

File.Copy(path, path + ".bak", overwrite: true);
File.Move(path + ".bak", Path.Combine(folder, "customers-backup.txt"), overwrite: true);   // overwrite: .NET Core 3.0+

foreach (string f in Directory.EnumerateFiles(folder, "*.txt"))   // lazy; GetFiles builds a full array first
    Console.WriteLine(Path.GetFileName(f));              // order is not guaranteed

File.Delete(Path.Combine(folder, "missing.txt"));        // no exception if the file doesn't exist
""", "FileHelpers.cs")}
{C(r"""
var info = new FileInfo(path);
Console.WriteLine($"{info.Name}: {info.Length} bytes, modified {info.LastWriteTime:dd MMM HH:mm}");
File.AppendAllText(path, "Imran Shaikh,Mumbai,400001\n");
Console.WriteLine(info.Length);                          // OLD value — FileInfo cached it
info.Refresh();
Console.WriteLine(info.Length);                          // new value

var dir = new DirectoryInfo(folder);
long totalBytes = dir.EnumerateFiles("*", SearchOption.AllDirectories).Sum(f => f.Length);
Console.WriteLine($"{dir.Name} uses {totalBytes} bytes");

Directory.Delete(folder, recursive: true);               // without recursive: true, a non-empty folder throws IOException
""", "FileInfoDemo.cs")}
{tip("<code>if (File.Exists(p)) File.ReadAllText(p)</code> can still fail, because another process could delete or lock the file between the two calls. Use Exists for friendly messages, but still handle <code>FileNotFoundException</code>, <code>IOException</code> and <code>UnauthorizedAccessException</code>.")}

<h3>3. File.ReadLines vs File.ReadAllLines</h3>
<p>Last week's grade analyser read a small CSV, so loading the whole file was fine. A year of UPI transactions exported from a bank can run to millions of rows. <code>ReadAllLines</code> loads every line into a <code>string[]</code> before you see the first one. <code>ReadLines</code> is lazy: it reads one line, hands it to your loop, then reads the next.</p>
{C(r"""
using System.Globalization;

// upi-statement.csv
// Date,Payee,Amount
// 2026-11-01,Swiggy,456.00
// 2026-11-02,BESCOM,1830.50
// ... 2 million rows

decimal total = 0;
int rows = 0;
foreach (string line in File.ReadLines("upi-statement.csv").Skip(1))   // skip the header; memory stays flat
{
    string[] parts = line.Split(',');
    total += decimal.Parse(parts[2], CultureInfo.InvariantCulture);    // invariant: '.' is always the decimal point
    rows++;
}
Console.WriteLine($"{rows} payments, total ₹{total:N2}");

// Stops reading at the first match. ReadAllLines would load the whole file first.
string? firstRefund = File.ReadLines("upi-statement.csv").FirstOrDefault(l => l.Contains("REFUND"));
""", "StatementTotals.cs")}
{table(["","File.ReadAllLines","File.ReadLines"],[
["Returns","<code>string[]</code> (all lines)","<code>IEnumerable&lt;string&gt;</code> (lazy)"],
["Memory","Whole file at once","About one line at a time"],
["First line available","After the whole file is read","Immediately"],
["Can stop early","No, it's already read everything","Yes (break, First, Take)"],
["Enumerate twice","Free (it's an array)","Re-reads the file each time"],
["File stays open","Only during the call","Until the loop finishes or is disposed"],
["Use for","Small files you need random access to","Big files, one pass, early exit"]])}

<h3>4. Streams: FileStream, StreamReader, StreamWriter</h3>
<p>The one-call helpers use streams internally. Use streams yourself when you need control: append to a log while keeping it open, read a huge file in parts, set sharing, or copy binary data. Think in layers: <code>FileStream</code> moves bytes to and from disk, and <code>StreamWriter</code>/<code>StreamReader</code> convert between text and bytes and buffer it.</p>
{C(r"""
using System.Text;

// Writing: FileStream (bytes) wrapped by StreamWriter (text → bytes)
using (var fs = new FileStream("orders.log", FileMode.Append, FileAccess.Write, FileShare.Read, bufferSize: 64 * 1024))
using (var writer = new StreamWriter(fs, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false)))
{
    writer.WriteLine($"{DateTime.Now:O} ORD-1001 placed ₹1,180");
    writer.WriteLine($"{DateTime.Now:O} ORD-1002 placed ₹2,360");
}   // Dispose: StreamWriter flushes its buffer, then disposes the FileStream, which releases the OS handle

// Reading line by line with a convenience constructor (opens the FileStream for you)
using (var reader = new StreamReader("orders.log"))       // detects a BOM if there is one, else assumes UTF-8
{
    string? line;
    while ((line = reader.ReadLine()) is not null)
        Console.WriteLine(line);
}

// Binary copy: no encoding involved
using (var source = File.OpenRead("invoice-1001.pdf"))
using (var target = File.Create("invoice-1001-copy.pdf"))
{
    source.CopyTo(target);                                // copies in chunks; works for any size
}
""", "Streams.cs")}
<p>Wednesday covers <code>using</code> in depth. For now: anything you open, you dispose.</p>
{table(["FileMode","If the file exists","If it doesn't"],[
["<code>CreateNew</code>","IOException","Creates it"],
["<code>Create</code>","Truncates to 0 bytes","Creates it"],
["<code>Open</code>","Opens it","FileNotFoundException"],
["<code>OpenOrCreate</code>","Opens it (keeps content)","Creates it"],
["<code>Truncate</code>","Opens and empties it","FileNotFoundException"],
["<code>Append</code>","Opens, positions at the end (write only)","Creates it"]])}
{table(["FileShare","Other processes may…"],[
["<code>None</code>","Not open the file at all until you close it"],
["<code>Read</code>","Read it (typical for a log you're writing)"],
["<code>Write</code> / <code>ReadWrite</code>","Also write to it"],
["<code>Delete</code>","Delete or rename it"]])}
{warn("Buffered data lives in memory until it's flushed. If the process crashes before Flush/Dispose, those lines are lost. <code>writer.AutoFlush = true</code> flushes after every write, which is safer but slower. For important data, write to a temp file and swap it in (Saturday's project does this).", "Buffering")}

<h3>5. Async file APIs</h3>
<p>Disk I/O is slow compared to the CPU. The async methods let the thread do other work while the OS reads or writes, which matters in web servers and UI apps. You'll study async/await properly next week. For now, treat <code>await</code> as \"wait for this without blocking the thread\".</p>
{C(r"""
// Whole file
string settingsJson = await File.ReadAllTextAsync("settings.json");
await File.WriteAllTextAsync("report.txt", "Total GST collected: ₹12,400");
await File.AppendAllLinesAsync("audit.log", ["asha approved R-88"]);

// Stream lines asynchronously (.NET 7+): an IAsyncEnumerable<string>
int errorCount = 0;
await foreach (string line in File.ReadLinesAsync("app.log"))
    if (line.Contains("ERROR", StringComparison.Ordinal)) errorCount++;
Console.WriteLine($"{errorCount} errors");

// Full control: FileStreamOptions (.NET 6+) with real OS-level async I/O
var options = new FileStreamOptions
{
    Mode = FileMode.Create,
    Access = FileAccess.Write,
    Share = FileShare.None,
    Options = FileOptions.Asynchronous,
    BufferSize = 64 * 1024
};
await using var fs = new FileStream("big-export.csv", options);
await using var csv = new StreamWriter(fs);
await csv.WriteLineAsync("OrderId,Amount");
await csv.WriteLineAsync("ORD-1001,1180");
""", "AsyncFiles.cs")}
{tip("In a console app that reads one small file, sync and async behave about the same. Use the async versions in ASP.NET Core (Phase 2), where a blocked thread is a thread that can't serve another request.")}

<h3>6. Encodings, BOMs and the ₹ sign</h3>
{C(r"""
using System.Text;

string price = "₹499";
Console.WriteLine(price.Length);                           // 4 chars (UTF-16 code units)
Console.WriteLine(Encoding.UTF8.GetByteCount(price));      // 6 bytes: ₹ = E2 82 B9, plus 3 ASCII digits
Console.WriteLine(Encoding.Unicode.GetByteCount(price));   // 8 bytes in UTF-16

File.WriteAllText("a.txt", price);                         // UTF-8 without BOM (the default)
File.WriteAllText("b.txt", price, Encoding.UTF8);          // UTF-8 WITH BOM: Encoding.UTF8 writes EF BB BF
File.WriteAllText("c.txt", price, new UTF8Encoding(false));// explicitly no BOM
Console.WriteLine(new FileInfo("a.txt").Length);           // 6
Console.WriteLine(new FileInfo("b.txt").Length);           // 9

// Reading a legacy Windows-1252 export from an old accounting tool
Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);   // enables code pages like 1252 on .NET Core+
string legacy = File.ReadAllText("old-ledger.csv", Encoding.GetEncoding(1252));

// Make the Windows console print ₹ and Hindi text correctly
Console.OutputEncoding = Encoding.UTF8;
""", "Encodings.cs")}
{table(["Situation","Encoding to use"],[
["Anything new: JSON, logs, CSV for other programs","UTF-8 without BOM (the default)"],
["CSV you expect people to open in Excel","UTF-8 <b>with</b> BOM. Without it, Excel often shows ₹ as garbage like <code>â‚¹</code>"],
["Files from old Windows tools","Their code page (often 1252), after registering CodePagesEncodingProvider"],
["Talking to Windows APIs / some legacy formats","UTF-16 (<code>Encoding.Unicode</code>)"]])}
''',
["Joining paths with string concatenation (<code>dir + \"\\\\\" + file</code>), which breaks on Linux and in Docker.",
"Using relative paths for data files, then being surprised the file appears in a different folder depending on where the app was launched.",
"<code>File.ReadAllLines</code> on a multi-GB file, causing OutOfMemoryException or a long freeze.",
"Forgetting to dispose a StreamWriter: the last lines are never written and the file stays locked.",
"Using <code>Encoding.UTF8</code> to get \"UTF-8\" and accidentally adding a BOM that breaks a strict parser (or leaving it off when Excel needs it)."],
("35 min", ["Write a console app that takes a folder path as an argument and prints, per file extension, the count and total size (use <code>DirectoryInfo.EnumerateFiles</code> with <code>SearchOption.AllDirectories</code>). Show sizes in KB/MB.",
"Generate a 500,000-line CSV of fake UPI payments (date, payee, amount). Then total it once with <code>ReadAllLines</code> and once with <code>ReadLines</code>, and compare time and <code>GC.GetTotalMemory(false)</code> / <code>Process.GetCurrentProcess().PeakWorkingSet64</code>.",
"Write <code>AppendAudit(string user, string action)</code> that opens <code>audit.log</code> with <code>FileMode.Append</code> and <code>FileShare.Read</code> and writes a timestamped line. Open the file in an editor while the app runs, then check the line is there after the call returns."]),
[("What's the difference between Path.Combine and Path.Join?","Both add the right separator. Combine restarts from any later argument that is rooted (an absolute path), so earlier parts are thrown away. Join just joins all the parts. Join is safer when part of the path comes from a user."),
("Why can File.ReadLines handle a 5 GB file when ReadAllLines can't?","ReadLines is lazy: it gives you one line at a time, so memory stays about one line plus a buffer. ReadAllLines builds an array holding every line in memory."),
("What happens to text written to a StreamWriter that is never flushed or disposed?","It stays in the writer's memory buffer and may never reach the file. The file handle also stays open, which can lock the file on Windows.")],
[("Basic","What is the difference between File, FileInfo and FileStream?","File has static one-call helpers that work on a path (ReadAllText, Copy, Delete). FileInfo is an object for one file that caches its metadata (Length, timestamps) and has instance methods. FileStream is an open handle for reading and writing bytes, with your choice of mode, access, sharing and buffering."),
("Basic","How do you write paths that work on Windows and Linux?","Use Path.Combine or Path.Join, never hard-coded \\ or /. Use Path.GetFullPath, Path.GetDirectoryName and friends to take paths apart, and Environment.GetFolderPath for well-known folders. Also remember Linux file names are case-sensitive."),
("Basic","When would you use a stream instead of File.ReadAllText?","For large files (to avoid loading everything into memory), when you need to process data as it arrives, append over time while keeping the file open, read or write binary data, control sharing and locking, or pass data to an API that takes a Stream without saving it first."),
("Intermediate","What is a BOM and why does it matter?","A Byte Order Mark is a byte sequence at the start of a text file that marks its encoding (EF BB BF for UTF-8). .NET writes UTF-8 without a BOM by default, but Encoding.UTF8 includes one. Some parsers reject a BOM, while Excel needs one to read UTF-8 CSV correctly, so choose deliberately."),
("Intermediate","What do FileMode, FileAccess and FileShare control?","FileMode says what to do depending on whether the file exists (Create, CreateNew, Open, OpenOrCreate, Truncate, Append). FileAccess is what you will do (Read, Write, ReadWrite). FileShare is what other handles may do at the same time. FileShare.None gives you exclusive access on Windows. On Unix, .NET uses advisory locks, so only cooperating processes respect it."),
("Intermediate","Why isn't checking File.Exists before opening enough?","It's a time-of-check/time-of-use race: the file can be deleted, renamed or locked between the check and the open. You still need to handle FileNotFoundException, IOException and UnauthorizedAccessException. Exists is only a hint for friendlier messages.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "System.Text.Json: serialization, options, attributes and dynamic JSON",
"Turn C# objects into JSON and back with System.Text.Json: shape the output with options and attributes, round-trip records and immutable types, handle polymorphic data, and read unknown JSON with JsonDocument and JsonNode.",
[("Serialization","Converting an object into a format you can store or send, such as JSON text or UTF-8 bytes."),
("Deserialization","Rebuilding an object from that format."),
("System.Text.Json (STJ)","The JSON library built into .NET Core 3.0+. It's fast, UTF-8 based and the default in ASP.NET Core."),
("JsonSerializer","The static entry point: <code>Serialize</code>, <code>Deserialize&lt;T&gt;</code>, plus async versions that work on streams."),
("JsonSerializerOptions","Settings for naming, indentation, null handling, enum format, converters and escaping. Create it once and reuse it."),
("Naming policy","Rule that maps C# names to JSON names, e.g. camelCase (<code>customerName</code>) or snake_case (.NET 8)."),
("Converter","A class that controls how one type is written and read, e.g. <code>JsonStringEnumConverter</code>."),
("[JsonPropertyName]","Attribute that sets one property's JSON name."),
("[JsonIgnore]","Attribute that skips a property, always or only under a condition."),
("[JsonRequired]",".NET 7+ attribute: deserialization fails if the property is missing from the JSON."),
("Type discriminator","An extra JSON property (e.g. <code>\"mode\": \"upi\"</code>) that records which derived type an object was."),
("JsonDocument","Read-only, fast DOM over JSON. Uses pooled memory, so dispose it."),
("JsonNode","Mutable DOM (<code>JsonObject</code>, <code>JsonArray</code>, <code>JsonValue</code>) for reading and editing JSON without a C# class."),
("Source generation","A compile-time generator that writes the serialization code for you. It avoids reflection and is required for Native AOT.")],
["Defaults: property names unchanged (PascalCase), case-sensitive reading, compact output, enums as numbers, nulls written.",
"Only public properties are serialized by default; fields are ignored unless you set <code>IncludeFields</code> or use <code>[JsonInclude]</code>.",
"Unknown JSON properties are silently ignored when reading (configurable in .NET 8).",
"Create a <code>JsonSerializerOptions</code> once and reuse it. It caches type metadata, and it can't be changed after first use.",
"Non-ASCII characters (₹, हिंदी) are escaped as <code>\\uXXXX</code> by default. That's valid JSON but hard to read.",
"Nullable annotations aren't enforced when reading unless you opt in (.NET 9)."],
f'''
<h3>1. Serialize and deserialize</h3>
{C(r"""
using System.Text.Json;

var invoice = new Invoice
{
    Number = "INV-1001",
    CustomerName = "Asha Traders",
    IssuedOn = new DateOnly(2026, 11, 10),
    Amount = 1180.5m,
    Status = InvoiceStatus.Issued,
    Items = ["Pen", "Notebook"]
};

string json = JsonSerializer.Serialize(invoice);
Console.WriteLine(json);
// {"Number":"INV-1001","CustomerName":"Asha Traders","Gstin":null,"IssuedOn":"2026-11-10",
//  "Amount":1180.5,"Status":1,"Items":["Pen","Notebook"]}

Invoice? back = JsonSerializer.Deserialize<Invoice>(json);   // null if the JSON is literally "null"
Console.WriteLine(back?.CustomerName);                        // Asha Traders

// Lowercase keys don't match by default: case-sensitive
Invoice? lower = JsonSerializer.Deserialize<Invoice>("{\"number\":\"INV-9\"}");
Console.WriteLine(lower!.Number == "");                       // True — "number" was ignored

// Types go after top-level statements
public enum InvoiceStatus { Draft, Issued, Paid }

public class Invoice
{
    public string Number { get; set; } = "";
    public string CustomerName { get; set; } = "";
    public string? Gstin { get; set; }
    public DateOnly IssuedOn { get; set; }          // DateOnly/TimeOnly supported since .NET 7
    public decimal Amount { get; set; }
    public InvoiceStatus Status { get; set; }
    public List<string> Items { get; set; } = [];
}
""", "Program.cs")}
<p>Serialize also has <code>SerializeToUtf8Bytes</code> and <code>SerializeAsync(stream, value)</code>. Writing straight to a FileStream skips the intermediate string, which matters for big files.</p>

<h3>2. JsonSerializerOptions: shape the output</h3>
{C(r"""
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Unicode;

public static class JsonDefaults
{
    // One shared instance: options cache per-type metadata, and become read-only after first use
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,          // CustomerName → customerName
        PropertyNameCaseInsensitive = true,                         // read "CustomerName" or "customername" too
        WriteIndented = true,                                       // human-readable
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,   // omit null properties
        Converters = { new JsonStringEnumConverter() },             // "Issued" instead of 1
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)       // keep ₹ and हिंदी as-is instead of \u20B9
    };
}
""", "JsonDefaults.cs")}
{C(r"""
{
  "number": "INV-1001",
  "customerName": "Asha Traders",
  "issuedOn": "2026-11-10",
  "amount": 1180.5,
  "status": "Issued",
  "items": [
    "Pen",
    "Notebook"
  ]
}
""", "JsonSerializer.Serialize(invoice, JsonDefaults.Options)", lang="json")}
{C(r"""
var note = new { Note = "₹500 चाय" };
Console.WriteLine(JsonSerializer.Serialize(note));                          // {"Note":"\u20B9500 \u091A\u093E\u092F"}
Console.WriteLine(JsonSerializer.Serialize(note, JsonDefaults.Options));    // { "note": "₹500 चाय" } (indented)

// Web defaults: camelCase + case-insensitive + numbers may arrive as strings ("amount": "499")
var web = new JsonSerializerOptions(JsonSerializerDefaults.Web);
// .NET 9 also has a ready-made read-only instance: JsonSerializerOptions.Web

// .NET 8 naming policies
var snake = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };   // customer_name
""")}
{table(["Option","Default","Common choice"],[
["<code>PropertyNamingPolicy</code>","null (names unchanged)","<code>CamelCase</code> for web APIs"],
["<code>PropertyNameCaseInsensitive</code>","false","true when reading JSON people edit by hand"],
["<code>WriteIndented</code>","false","true for files people read; false for APIs"],
["<code>DefaultIgnoreCondition</code>","Never","<code>WhenWritingNull</code>"],
["Enum format","Number","<code>JsonStringEnumConverter</code> (stable if you reorder members)"],
["<code>Encoder</code>","Escapes non-ASCII and HTML-sensitive characters","<code>JavaScriptEncoder.Create(UnicodeRanges.All)</code> for files"],
["<code>NumberHandling</code>","Strict","<code>AllowReadingFromString</code> (Web defaults)"],
["<code>UnmappedMemberHandling</code> (.NET 8)","Skip unknown properties","<code>Disallow</code> for strict contracts"]])}
{warn("Writing <code>new JsonSerializerOptions { ... }</code> inside a method that runs per request or per record throws away the metadata cache each time. That makes it much slower, and in older .NET versions it also leaked memory. Store options in a <code>static readonly</code> field.", "Performance")}

<h3>3. Attributes for per-property control</h3>
<p>Options apply to every type. Attributes change a single property, which is useful when you match an external contract like a payment webhook with snake_case names.</p>
{C(r"""
using System.Text.Json.Serialization;

public class UpiWebhook
{
    [JsonPropertyName("txn_id")]
    public string TransactionId { get; set; } = "";

    [JsonRequired]                                   // .NET 7+: missing "amount" → JsonException
    [JsonPropertyName("amount")]
    public decimal Amount { get; set; }

    [JsonPropertyName("payer_vpa")]
    public string? PayerVpa { get; set; }            // e.g. asha@okhdfc

    [JsonIgnore]                                     // never read or written
    public string? InternalNotes { get; set; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    [JsonPropertyName("retry_count")]
    public int RetryCount { get; set; }              // left out of the output when 0

    [JsonInclude]                                    // non-public setter is used when reading
    [JsonPropertyName("received_at")]
    public DateTime ReceivedAt { get; private set; } = DateTime.UtcNow;

    [JsonPropertyOrder(-1)]                          // written first
    [JsonPropertyName("event")]
    public string Event { get; set; } = "payment.captured";
}
""", "UpiWebhook.cs")}
{C(r"""
string body = QQQ{"event":"payment.captured","txn_id":"T2611101234","amount":2360,"payer_vpa":"asha@okhdfc","InternalNotes":"x"}QQQ;
var hook = JsonSerializer.Deserialize<UpiWebhook>(body)!;
Console.WriteLine($"{hook.TransactionId} {hook.Amount} {hook.InternalNotes ?? "(ignored)"}");
// T2611101234 2360 (ignored)

try
{
    JsonSerializer.Deserialize<UpiWebhook>(QQQ{"txn_id":"T1"}QQQ);
}
catch (JsonException ex)
{
    Console.WriteLine(ex.Message);   // JSON deserialization for type 'UpiWebhook' was missing required properties, including the following: amount
}
""")}
{table(["Attribute","Effect"],[
["<code>[JsonPropertyName(\"x\")]</code>","Use this JSON name (overrides the naming policy)"],
["<code>[JsonIgnore]</code>","Skip always; with <code>Condition</code>: WhenWritingNull / WhenWritingDefault"],
["<code>[JsonRequired]</code> or C# <code>required</code>","Must be present when reading (.NET 7+)"],
["<code>[JsonInclude]</code>","Include a field, or use non-public accessors"],
["<code>[JsonConstructor]</code>","Pick which constructor to use when reading"],
["<code>[JsonPropertyOrder(n)]</code>","Control output order"],
["<code>[JsonConverter(typeof(...))]</code>","Custom converter for this property or type"],
["<code>[JsonNumberHandling(...)]</code>","Allow numbers as strings for this member"]])}

<h3>4. Records, immutable types and missing data</h3>
<p>STJ can create objects through a constructor. It matches each parameter to a property with the same name (ignoring case), which is why positional records just work.</p>
{C(r"""
using System.Text.Json;

var e = new Expense(1, new DateOnly(2026, 11, 3), "Groceries", 1249.75m, "BigBasket order");
string json = JsonSerializer.Serialize(e, JsonDefaults.Options);
Expense copy = JsonSerializer.Deserialize<Expense>(json, JsonDefaults.Options)!;
Console.WriteLine(copy == e);            // True — value equality, built through the constructor

var c = JsonSerializer.Deserialize<Customer>(QQQ{"name":"Ravi Kumar","pin":"600001"}QQQ, JsonDefaults.Options)!;
Console.WriteLine($"{c.Name} {c.Pin}");  // Ravi Kumar 600001

// ❌ A missing value for a non-nullable property is NOT an error by default
var bad = JsonSerializer.Deserialize<Expense>(QQQ{"id":2,"date":"2026-11-04","amount":99}QQQ, JsonDefaults.Options)!;
Console.WriteLine(bad.Category is null); // True — even though Category is declared as non-nullable string

// .NET 9 opt-ins make it strict
var strict = new JsonSerializerOptions(JsonDefaults.Options)   // copy constructor
{
    RespectNullableAnnotations = true,            // null for a non-nullable property → JsonException
    RespectRequiredConstructorParameters = true   // missing non-optional constructor parameter → JsonException
};

public sealed record Expense(int Id, DateOnly Date, string Category, decimal Amount, string? Note = null);

public sealed class Customer
{
    public required string Name { get; init; }    // C# 11 required: STJ (.NET 7+) enforces it like [JsonRequired]
    public required string Pin { get; init; }
    public string? Email { get; init; }
}
""", "Records.cs")}
{tip("Validate after deserializing, whatever the options say. JSON from files and APIs is user input: check ranges, enums (<code>Enum.IsDefined</code>) and business rules. Saturday's <code>Expense.Validate()</code> does exactly this.")}

<h3>5. Polymorphism with [JsonDerivedType] (.NET 7+)</h3>
<p>If you serialize a <code>List&lt;Payment&gt;</code> without help, STJ writes only the base type's properties and can't tell which subtype to create when reading. Declare the derived types and a discriminator property.</p>
{C(r"""
using System.Text.Json.Serialization;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "mode")]   // default name is "$type"
[JsonDerivedType(typeof(UpiPayment), "upi")]
[JsonDerivedType(typeof(CardPayment), "card")]
[JsonDerivedType(typeof(CashPayment), "cash")]
public abstract record Payment(decimal Amount);

public sealed record UpiPayment(decimal Amount, string Vpa) : Payment(Amount);
public sealed record CardPayment(decimal Amount, string Last4, string Network) : Payment(Amount);
public sealed record CashPayment(decimal Amount) : Payment(Amount);
""", "Payments.cs")}
{C(r"""
List<Payment> payments =
[
    new UpiPayment(450m, "ravi@okicici"),
    new CardPayment(2999m, "4242", "RuPay"),
    new CashPayment(120m)
];

string json = JsonSerializer.Serialize(payments, JsonDefaults.Options);
// each object starts with "mode": "upi" / "card" / "cash", followed by its own properties

List<Payment> back = JsonSerializer.Deserialize<List<Payment>>(json, JsonDefaults.Options)!;
foreach (Payment p in back)
{
    Console.WriteLine(p switch
    {
        UpiPayment u  => $"UPI ₹{u.Amount} from {u.Vpa}",
        CardPayment c => $"{c.Network} card ****{c.Last4}: ₹{c.Amount}",
        CashPayment   => $"Cash ₹{p.Amount}",
        _             => "Unknown"
    });
}
// UPI ₹450 from ravi@okicici
// RuPay card ****4242: ₹2999
// Cash ₹120
""")}
{warn("The discriminator is written only when the <b>declared</b> type is the base: <code>Serialize&lt;Payment&gt;(upi)</code> or a <code>List&lt;Payment&gt;</code>. <code>Serialize(upi)</code>, where the declared type is UpiPayment, has no <code>mode</code> property, so you can't read it back as a Payment. Up to .NET 8 the discriminator must also be the first property in the JSON. .NET 9 adds <code>AllowOutOfOrderMetadataProperties</code>.", "Gotcha")}

<h3>6. Dynamic JSON: JsonDocument and JsonNode, plus source generation</h3>
<p>Sometimes you only need two fields from a big API response, or the shape isn't known in advance. You don't need to write a class for that.</p>
{C(r"""
using System.Text.Json;
using System.Text.Json.Nodes;

string response = QQQ
    {
      "pincode": "560001",
      "postOffices": [
        { "name": "Bangalore GPO", "district": "Bengaluru", "state": "Karnataka" },
        { "name": "Vidhana Soudha", "district": "Bengaluru", "state": "Karnataka" }
      ]
    }
    QQQ;

// JsonDocument: read-only and fast; rents pooled memory, so dispose it
using (JsonDocument doc = JsonDocument.Parse(response))
{
    JsonElement root = doc.RootElement;
    JsonElement offices = root.GetProperty("postOffices");
    Console.WriteLine($"{offices[0].GetProperty("state").GetString()}: {offices.GetArrayLength()} offices");
    // Karnataka: 2 offices

    foreach (JsonElement office in offices.EnumerateArray())
        Console.WriteLine(office.GetProperty("name").GetString());

    if (!root.TryGetProperty("deliveryStatus", out _))       // GetProperty would throw KeyNotFoundException
        Console.WriteLine("No deliveryStatus field");
}

// JsonNode: mutable; good for patching JSON
JsonNode node = JsonNode.Parse(response)!;
node["pincode"] = "560002";
node["postOffices"]!.AsArray().Add(new JsonObject { ["name"] = "Shivajinagar", ["state"] = "Karnataka" });
Console.WriteLine(node["postOffices"]![2]!["name"]!.GetValue<string>());   // Shivajinagar
Console.WriteLine(node.ToJsonString());                                    // compact JSON with the changes
""", "DynamicJson.cs")}
{table(["","JsonSerializer + class","JsonDocument","JsonNode"],[
["Needs a C# type","Yes","No","No"],
["Editable","Edit the object","No (read-only)","Yes"],
["Speed / memory","Fast","Fastest for reading parts","Slower, allocates more"],
["Must dispose","No","Yes","No"],
["Use for","Known contracts","Peeking into large or unknown JSON","Patching or building JSON on the fly"]])}
<h4>Source generation (awareness)</h4>
{C(r"""
using System.Text.Json;
using System.Text.Json.Serialization;

[JsonSourceGenerationOptions(WriteIndented = true, PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
                             UseStringEnumConverter = true)]            // UseStringEnumConverter: .NET 8
[JsonSerializable(typeof(List<Invoice>))]
internal partial class AppJsonContext : JsonSerializerContext { }

// Usage: pass the generated type info instead of options
string json = JsonSerializer.Serialize(invoices, AppJsonContext.Default.ListInvoice);
List<Invoice>? list = JsonSerializer.Deserialize(json, AppJsonContext.Default.ListInvoice);
""", "AppJsonContext.cs")}
<p>The generator writes the property-by-property code at compile time. That gives faster startup, no reflection, trimming safety and Native AOT support. You'll mainly see it in high-performance APIs and AOT-published tools. Reflection mode (everything above) is fine for most apps.</p>
''',
["Creating a new <code>JsonSerializerOptions</code> on every call.",
"Expecting lowercase JSON keys to bind to PascalCase properties without <code>PropertyNameCaseInsensitive</code> or a camelCase policy.",
"Storing enums as numbers in files, then reordering the enum members and silently corrupting old data.",
"Trusting deserialized data: missing required fields arrive as null/0 unless you mark them required, and values still need validating.",
"Forgetting to dispose <code>JsonDocument</code>, which leaks pooled buffers."],
("35 min", ["Model an Indian GST invoice: seller and buyer (name, GSTIN, state), line items (HSN code, qty, rate) and computed CGST/SGST or IGST. Serialize it with camelCase, indented output, string enums and nulls omitted, then read it back and assert the totals match.",
"Write a <code>UpiWebhook</code> class for a snake_case payload, mark <code>txn_id</code> and <code>amount</code> as required, and show what happens with a missing field, an unknown extra field, and <code>\"amount\": \"499\"</code> (try with and without Web defaults).",
"Use <code>JsonNode</code> to load a <code>settings.json</code>, change one nested value (e.g. <code>gst.ratePercent</code> to 12), add a new property, and write it back indented, without defining any C# class."]),
[("What are System.Text.Json's defaults for property names and enums?","Property names stay as written in C# (PascalCase), matching is case-sensitive when reading, and enums are written as numbers. Use a naming policy and JsonStringEnumConverter to change this."),
("How do you make a property mandatory when deserializing?","Mark it [JsonRequired] or use the C# required modifier (both .NET 7+). If it's missing, deserialization throws JsonException. In .NET 9 you can also turn on RespectRequiredConstructorParameters for records."),
("When would you use JsonDocument instead of a class?","When you only need a few values from large or unknown JSON, or the shape varies. JsonDocument reads without allocating a full object graph. It's read-only and must be disposed.")],
[("Basic","How do you serialize an object to camelCase, indented JSON with string enums?","Create a JsonSerializerOptions with PropertyNamingPolicy = JsonNamingPolicy.CamelCase, WriteIndented = true and Converters.Add(new JsonStringEnumConverter()). Store it in a static field and pass it to Serialize/Deserialize."),
("Basic","What does [JsonIgnore] do, and what are its conditions?","It excludes a property from serialization and deserialization. With Condition you can exclude it only WhenWritingNull or WhenWritingDefault, or explicitly Never. The global DefaultIgnoreCondition option applies the same rule to every property."),
("Basic","Why should JsonSerializerOptions be reused?","Each instance builds and caches metadata for every type it handles. Creating new options per call rebuilds that cache every time, which is slow and in old versions leaked memory. Options also become immutable after first use, so a shared static instance is the intended pattern."),
("Intermediate","How does System.Text.Json deserialize immutable records?","It uses the public constructor (or the one marked [JsonConstructor]) and matches each parameter to a property of the same name, ignoring case. JSON properties are matched to those properties first, so naming policies apply. Missing parameters get default values unless you enable .NET 9's RespectRequiredConstructorParameters."),
("Intermediate","How do you serialize a polymorphic hierarchy?","Put [JsonPolymorphic] and one [JsonDerivedType(typeof(Sub), \"discriminator\")] per subtype on the base type (.NET 7+). Serialize through the base type so the discriminator is written. When reading, STJ uses it to pick the subtype. Before .NET 7 you needed a custom JsonConverter."),
("Intermediate","What are the benefits of System.Text.Json source generation?","The serializer code is generated at compile time from a JsonSerializerContext. That means no runtime reflection, faster startup, lower memory use, trimming safety and Native AOT support. The cost is declaring every root type with [JsonSerializable] and some extra build setup.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "IDisposable, using, the Dispose pattern and IAsyncDisposable",
"Release files, sockets and other OS resources at the right moment: use <code>using</code> statements and declarations, implement IDisposable correctly (including the full pattern and why SafeHandle replaces finalizers), use <code>await using</code>, and spot resource leaks.",
[("Managed resource","Memory the GC owns: ordinary .NET objects. The GC frees it eventually."),
("Unmanaged resource","Something outside the GC: file handles, sockets, database connections, OS locks, native memory."),
("IDisposable","Interface with one method, <code>Dispose()</code>, meaning \"release your resources now\"."),
("Deterministic cleanup","Releasing a resource at a known point in the code, rather than whenever the GC runs."),
("using statement","<code>using (var x = ...) { }</code>: calls Dispose at the closing brace, even if an exception is thrown."),
("using declaration","C# 8 <code>using var x = ...;</code>: calls Dispose at the end of the enclosing scope."),
("Finalizer","<code>~ClassName()</code>: runs on the GC's finalizer thread at an unpredictable time. A last-chance cleanup."),
("GC.SuppressFinalize","Tells the GC that this object's finalizer no longer needs to run, because Dispose already cleaned up."),
("Dispose pattern","<code>Dispose()</code> plus <code>protected virtual Dispose(bool disposing)</code>, so subclasses can add their own cleanup."),
("SafeHandle","A built-in wrapper around an OS handle that has its own reliable finalizer, so you don't write finalizers yourself."),
("ObjectDisposedException","Thrown when someone uses an object after it was disposed."),
("IAsyncDisposable","Interface with <code>ValueTask DisposeAsync()</code> for cleanup that does I/O (flushing to disk or the network)."),
("await using","Calls DisposeAsync at the end of the scope."),
("Ownership","Whoever creates a disposable (or is handed ownership) is responsible for disposing it.")],
["The GC frees memory, not files or connections. Dispose releases those right away.",
"If a type implements IDisposable, assume you must dispose it, unless documentation says otherwise or a DI container owns it.",
"<code>using</code> compiles into try/finally, so Dispose runs even when an exception is thrown.",
"With several using declarations, objects are disposed in reverse order.",
"Dispose must be safe to call more than once and shouldn't throw.",
"You almost never need a finalizer: wrap OS handles in SafeHandle, or just own other disposables."],
f'''
<h3>1. Why Dispose exists</h3>
<p>The garbage collector runs when <i>memory</i> is low. It doesn't know that a small <code>FileStream</code> object is holding an OS file handle that another program needs. Until that object is collected and finalized, which could be minutes later or never in a short app, the file stays open.</p>
{C(r"""
// ❌ Never disposed
var writer = new StreamWriter("audit.log");
writer.WriteLine("Login: asha@example.com");
// 1. The line is probably still in the writer's buffer, not on disk.
// 2. The file handle is still open. On Windows:
File.Delete("audit.log");   // IOException: The process cannot access the file because it is being used by another process.

// ✓ Disposed: flushed and closed immediately
using (var w = new StreamWriter("audit2.log"))
{
    w.WriteLine("Login: asha@example.com");
}
File.Delete("audit2.log");  // works
""", "Leak.cs")}

<h3>2. using statements and using declarations</h3>
{C(r"""
// using statement: Dispose at the closing brace
using (var reader = new StreamReader("orders.csv"))
{
    Console.WriteLine(reader.ReadLine());
}   // reader.Dispose() here

// using declaration (C# 8): Dispose at the end of the enclosing block
static int CountOrders(string path)
{
    using var reader = new StreamReader(path);
    int count = 0;
    while (reader.ReadLine() is not null) count++;
    return count;
}   // reader.Dispose() here, even if ReadLine throws

// What the compiler generates for a using statement (roughly)
StreamReader r = new StreamReader("orders.csv");
try
{
    Console.WriteLine(r.ReadLine());
}
finally
{
    r?.Dispose();
}
""", "UsingForms.cs")}
<h4>Disposal order</h4>
{C(r"""
using var connection = new Step("connection");
using var transaction = new Step("transaction");
Console.WriteLine("doing work");

// doing work
// dispose transaction
// dispose connection        ← reverse order: inner resources first

sealed class Step(string name) : IDisposable
{
    public void Dispose() => Console.WriteLine($"dispose {name}");
}
""", "DisposeOrder.cs")}
{tip("Use a using <b>statement</b> (with braces) when the resource should be released before the method ends, for example to unlock a file before you move it. A using <b>declaration</b> keeps it open until the end of the block, which is sometimes longer than you think.")}

<h3>3. Implementing IDisposable (the simple, sealed version)</h3>
<p>Most classes you write don't own raw OS handles. They own <i>other disposables</i> (a StreamWriter, an HttpClient, a DbConnection). For a sealed class, Dispose just disposes what it owns.</p>
{C(r"""
using System.Text;

public sealed class AuditLog : IDisposable
{
    private readonly StreamWriter _writer;
    private bool _disposed;

    public AuditLog(string path)
    {
        var stream = new FileStream(path, FileMode.Append, FileAccess.Write, FileShare.Read);
        _writer = new StreamWriter(stream, new UTF8Encoding(false));   // the writer now owns the stream
    }

    public void Write(string user, string action)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);              // .NET 7+
        _writer.WriteLine($"{DateTime.UtcNow:O}\t{user}\t{action}");
    }

    public void Dispose()
    {
        if (_disposed) return;          // calling twice is harmless
        _writer.Dispose();              // flushes, then disposes the FileStream
        _disposed = true;
    }
}
""", "AuditLog.cs")}
{C(r"""
using (var audit = new AuditLog("audit.log"))
{
    audit.Write("asha", "approved refund R-88");
    audit.Write("ravi", "changed GSTIN for C-1042");
}

var closed = new AuditLog("audit.log");
closed.Dispose();
closed.Write("meena", "late write");   // ObjectDisposedException: Cannot access a disposed object. Object name: 'AuditLog'.
""")}

<h3>4. The full Dispose pattern, finalizers and SafeHandle</h3>
<p>If your class is <b>not sealed</b>, subclasses may own resources too. The standard pattern gives them a <code>protected virtual Dispose(bool)</code> to override.</p>
{C(r"""
public class ReportExporter : IDisposable
{
    private readonly FileStream _output;
    private bool _disposed;

    public ReportExporter(string path) => _output = File.Create(path);

    protected Stream Output => _output;

    public void Dispose()
    {
        Dispose(disposing: true);
        GC.SuppressFinalize(this);       // if a subclass adds a finalizer, it no longer needs to run
    }

    protected virtual void Dispose(bool disposing)
    {
        if (_disposed) return;
        if (disposing)
        {
            _output.Dispose();           // managed objects: only touch them when called from Dispose()
        }
        // raw unmanaged resources (IntPtr handles) would be freed here — but use SafeHandle instead
        _disposed = true;
    }
}

public class GstReportExporter : ReportExporter
{
    private readonly StreamWriter _summary;
    private bool _disposed;

    public GstReportExporter(string path) : base(path) =>
        _summary = new StreamWriter(path + ".summary.txt");

    protected override void Dispose(bool disposing)
    {
        if (!_disposed)
        {
            if (disposing) _summary.Dispose();
            _disposed = true;
        }
        base.Dispose(disposing);         // always let the base class clean up too
    }
}
""", "ReportExporter.cs")}
{table(["Called from","disposing","Safe to touch other managed objects?"],[
["<code>Dispose()</code> (your code)","true","Yes: they're still alive"],
["Finalizer (GC thread)","false","No: they may already be finalized; free only raw unmanaged resources"]])}
<h4>Finalizers: awareness only</h4>
{C(r"""
// Only if a class DIRECTLY holds a raw unmanaged resource (rare in modern .NET):
~ReportExporter() => Dispose(disposing: false);
// Costs: the object survives at least one extra GC, the finalizer runs on a single
// background thread at an unknown time, and it may not run at all if the process is killed.
""")}
<p>Instead of an <code>IntPtr</code> plus a finalizer, .NET wraps OS handles in <code>SafeHandle</code> subclasses (<code>SafeFileHandle</code>, <code>SafeWaitHandle</code>…). They already have a reliable finalizer, so <i>your</i> class only owns a disposable and uses the simple pattern.</p>
{C(r"""
using Microsoft.Win32.SafeHandles;

// .NET 6+: open a raw handle and read at an offset without a FileStream
using SafeFileHandle handle = File.OpenHandle("ledger.dat", FileMode.Open, FileAccess.Read);
byte[] header = new byte[16];
int read = RandomAccess.Read(handle, header, fileOffset: 0);
Console.WriteLine($"Read {read} header bytes, file is {RandomAccess.GetLength(handle)} bytes");
""", "SafeHandleDemo.cs")}

<h3>5. IAsyncDisposable and await using</h3>
<p>Disposing a writer flushes its buffer, which is I/O. <code>DisposeAsync</code> lets that flush happen without blocking a thread. Types like <code>FileStream</code>, <code>StreamWriter</code>, <code>DbConnection</code> and <code>Utf8JsonWriter</code> implement both interfaces.</p>
{C(r"""
public sealed class CsvExportWriter : IAsyncDisposable
{
    private readonly StreamWriter _writer;

    public CsvExportWriter(string path) =>
        _writer = new StreamWriter(new FileStream(path, FileMode.Create, FileAccess.Write,
                                                  FileShare.None, bufferSize: 4096, useAsync: true));

    public Task WriteRowAsync(params string[] cells) => _writer.WriteLineAsync(string.Join(',', cells));

    public async ValueTask DisposeAsync()
    {
        await _writer.FlushAsync();      // flush without blocking a thread
        await _writer.DisposeAsync();    // also disposes the FileStream
    }
}
""", "CsvExportWriter.cs")}
{C(r"""
await using (var csv = new CsvExportWriter("gstr1-nov-2026.csv"))
{
    await csv.WriteRowAsync("Invoice", "GSTIN", "Taxable", "GST");
    await csv.WriteRowAsync("INV-1001", "29ABCDE1234F1Z5", "1000", "180");
}   // await csv.DisposeAsync() here

// declaration form
await using var another = new CsvExportWriter("gstr1-dec-2026.csv");
""")}
{tip("If a type implements both interfaces, <code>await using</code> calls DisposeAsync and <code>using</code> calls Dispose. In async methods, prefer <code>await using</code> for anything that flushes.")}

<h3>6. Ownership and common leaks</h3>
{C(r"""
// A StreamReader disposes the stream it wraps — unless you say leaveOpen
using var file = File.OpenRead("orders.csv");
using (var reader = new StreamReader(file, leaveOpen: true))
{
    Console.WriteLine(reader.ReadLine());   // header
}
file.Position = 0;                           // still usable because of leaveOpen: true

// A method that RETURNS a disposable transfers ownership to the caller
static StreamWriter OpenDailyLog(DateOnly day) =>
    new StreamWriter(Path.Combine("logs", $"{day:yyyy-MM-dd}.log"), append: true);

using var log = OpenDailyLog(DateOnly.FromDateTime(DateTime.Today));   // caller disposes
""", "Ownership.cs")}
{table(["Leak","What happens","Fix"],[
["Stream or writer not disposed","File locked, last data lost","<code>using</code> / <code>await using</code>"],
["Disposing a stream the caller still needs","ObjectDisposedException later","<code>leaveOpen: true</code>, or don't dispose what you don't own"],
["<code>new HttpClient()</code> per request, disposed each time","Sockets pile up in TIME_WAIT (socket exhaustion)","Reuse one instance or use IHttpClientFactory (Phase 2)"],
["Event subscriptions never removed (Week 3)","Publisher keeps subscribers alive","Unsubscribe in Dispose"],
["<code>Timer</code> not disposed","Callbacks keep firing","Dispose it when done"],
["<code>CancellationTokenSource</code> with CancelAfter not disposed","Internal timer kept alive","<code>using var cts = ...</code>"],
["Disposing services you got from DI","Breaks other users of the shared instance","The container owns what it creates"]])}
''',
["Relying on the GC (or a finalizer) to close files and connections.",
"Writing a finalizer \"just in case\" in a class that only owns managed disposables. It adds GC cost and gives no benefit.",
"Touching other managed objects inside the <code>disposing == false</code> path.",
"Disposing an object you don't own: a stream passed in by the caller, or a service resolved from DI.",
"Forgetting that a using declaration keeps the resource open until the end of the block, e.g. trying to move a file you still have open."],
("35 min", ["Write a sealed <code>TempWorkspace : IDisposable</code> that creates a unique folder under <code>Path.GetTempPath()</code> in its constructor and deletes it (recursively) in Dispose. Make Dispose idempotent and make other members throw ObjectDisposedException after disposal.",
"Write <code>Step(string name)</code> as in the notes and nest three using declarations and one using statement inside a method that throws halfway. Predict the printed order first, then run it.",
"Convert <code>AuditLog</code> to also implement <code>IAsyncDisposable</code> with a <code>WriteAsync</code> method. Use it with <code>await using</code> and check the last line is on disk after the block."]),
[("Does the GC call Dispose?","No. The GC only calls finalizers, and only for objects that have one. Dispose is called by your code (using) or by a DI container that owns the object."),
("Why call GC.SuppressFinalize(this) in Dispose()?","Dispose has already cleaned up, so the finalizer is unnecessary. Suppressing it lets the object be collected in one GC instead of being queued for finalization first."),
("When is Dispose called for a using declaration?","At the end of the enclosing scope (block or method), including when an exception leaves that scope. Multiple declarations are disposed in reverse order.")],
[("Basic","What is IDisposable and why is it needed in a garbage-collected language?","It's the contract for deterministic cleanup. The GC reclaims memory, but it doesn't know when to release OS resources like file handles, sockets or DB connections, and may not run for a long time. Dispose releases them immediately when you're done."),
("Basic","What is the difference between a using statement and a using declaration?","A using statement has its own block and disposes at the closing brace. A using declaration (C# 8) has no braces and disposes at the end of the enclosing scope. Both compile to try/finally, so disposal also happens on exceptions."),
("Basic","Explain Dispose vs Finalize.","Dispose is called explicitly (deterministic) and can clean up both managed and unmanaged resources. A finalizer is called by the GC at a nondeterministic time on the finalizer thread, may never run, delays collection, and must only free unmanaged resources. Modern code uses SafeHandle instead of writing finalizers."),
("Intermediate","Describe the full Dispose pattern and when you need it.","Public Dispose() calls protected virtual Dispose(true) and then GC.SuppressFinalize(this). Dispose(bool disposing) frees managed resources only when disposing is true, frees unmanaged ones in both cases, and guards with a _disposed flag. Subclasses override Dispose(bool) and call base. You need it for unsealed classes that own resources. Sealed classes can use a simple Dispose."),
("Intermediate","What is SafeHandle and why prefer it over a finalizer?","SafeHandle is a built-in abstract wrapper around an OS handle. It has a critical finalizer and reference counting that protects against handle recycling and early release during native calls. Wrapping handles in SafeHandle means your own classes never need finalizers."),
("Intermediate","When should a type implement IAsyncDisposable?","When cleanup involves I/O that has an async version, such as flushing a buffered stream or closing a network or database connection. DisposeAsync lets that work run without blocking a thread. Types often implement both interfaces, and await using prefers DisposeAsync.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Logging with ILogger in a console app",
"Replace Console.WriteLine debugging with Microsoft.Extensions.Logging: create loggers from a LoggerFactory, pick the right log level, write structured messages with templates, add scopes, and filter noise by category.",
[("Microsoft.Extensions.Logging (MEL)","The standard .NET logging abstraction used by ASP.NET Core, EF Core and the Generic Host."),
("ILogger / ILogger&lt;T&gt;","The interface you log through. <code>ILogger&lt;OrderImporter&gt;</code> uses the type's full name as its category."),
("ILoggerFactory","Creates loggers and owns the providers. Dispose it to flush pending messages."),
("Logging provider","A destination: Console, Debug, EventLog, or third-party ones like Serilog sinks and OpenTelemetry exporters."),
("Category","A logger's name, usually the class name. Filters are applied by category prefix."),
("Log level","How serious a message is: Trace, Debug, Information, Warning, Error, Critical (and None)."),
("Message template","A message with named placeholders, <code>\"Order {OrderId} paid\"</code>, with the values passed separately."),
("Structured logging","Keeping each placeholder value as a named field, so log tools can search and aggregate (<code>OrderId = ORD-1042</code>)."),
("EventId","A numeric ID (plus optional name) identifying a kind of event, useful for alerts and filtering."),
("Scope","Context (like a file name or request ID) attached to every message logged inside a <code>using (logger.BeginScope(...))</code> block."),
("Filter rule","A minimum level per category and/or provider, e.g. <code>\"Microsoft\": \"Warning\"</code>."),
("Formatter","How the console provider renders a message: simple, systemd or JSON."),
("LoggerMessage source generator",".NET 6+ attribute that generates fast, allocation-light logging methods at compile time.")],
["Log through ILogger, not Console.WriteLine, so messages get levels, categories and filtering, and can go anywhere.",
"Use message templates, never <code>$\"...\"</code> interpolation, so values stay structured.",
"Exceptions go in the <b>first</b> argument: <code>LogError(ex, \"Could not save {Path}\", path)</code>.",
"Placeholders are filled by <b>position</b>, not by name.",
"The default minimum level is Information, so Debug and Trace are hidden until you lower it.",
"The console provider writes on a background thread. Dispose the factory (or host) so the last messages appear."],
f'''
<h3>1. Why not Console.WriteLine?</h3>
{table(["Need","Console.WriteLine","ILogger"],[
["Severity","None: every line looks the same","Trace … Critical"],
["Turn off noisy parts in production","Edit and redeploy code","Change config: <code>\"OrderImporter\": \"Warning\"</code>"],
["Know where a message came from","Only if you type it","Category = class name, plus EventId"],
["Search \"all failures for ORD-1042\"","grep through text","Query the structured <code>OrderId</code> field"],
["Send to files, Azure, Seq, Elastic","Rewrite every call","Add a provider; calls don't change"],
["Exceptions with stack traces","Manual formatting","<code>LogError(ex, ...)</code>"],
["Library code","Pollutes the app's console","Libraries accept an ILogger, and the app decides"]])}
<p>Console.WriteLine is still right for <b>user-facing output</b>, like the menus and tables in your console apps. Logging is for <b>operators and developers</b>: what the program did, how long it took, and what went wrong.</p>

<h3>2. Set up logging in a console app</h3>
{C(r"""
dotnet new console -n OrderImporter
cd OrderImporter
dotnet add package Microsoft.Extensions.Logging
dotnet add package Microsoft.Extensions.Logging.Console
""", lang="bash")}
{C(r"""
using Microsoft.Extensions.Logging;

using ILoggerFactory factory = LoggerFactory.Create(builder =>
{
    builder
        .SetMinimumLevel(LogLevel.Debug)              // default would be Information
        .AddSimpleConsole(options =>
        {
            options.SingleLine = true;
            options.TimestampFormat = "HH:mm:ss ";
            options.IncludeScopes = true;
        });
});

ILogger<Program> log = factory.CreateLogger<Program>();          // category "Program"
ILogger csvLog = factory.CreateLogger("OrderImporter.Csv");      // category by name

log.LogInformation("Importer started with {ArgCount} arguments", args.Length);
log.LogDebug("Working directory is {Directory}", Environment.CurrentDirectory);
log.LogWarning("Disk space low: {FreeGb} GB left", 3.5);
csvLog.LogTrace("This is hidden: Trace is below the Debug minimum");

// 10:15:02 info: Program[0] Importer started with 0 arguments
// 10:15:02 dbug: Program[0] Working directory is /home/priya/OrderImporter
// 10:15:02 warn: Program[0] Disk space low: 3.5 GB left
""", "Program.cs")}
<p>The <code>[0]</code> is the EventId. When you pass a class as the type argument, as in <code>CreateLogger&lt;OrderImporter&gt;()</code>, the category is its full name, e.g. <code>OrderImporter.Services.CsvReader</code>. Classes don't create loggers themselves. They ask for one in the constructor, which is how DI will hand it over on Friday and in ASP.NET Core:</p>
{C(r"""
using Microsoft.Extensions.Logging;

public sealed class OrderImporter(ILogger<OrderImporter> logger)
{
    public int Import(string path)
    {
        logger.LogInformation("Importing {Path}", path);
        int count = File.ReadLines(path).Skip(1).Count();
        logger.LogInformation("Imported {Count} orders from {Path}", count, path);
        return count;
    }
}

// In Program.cs (no DI yet): new OrderImporter(factory.CreateLogger<OrderImporter>())
""", "OrderImporter.cs")}

<h3>3. Log levels</h3>
{table(["Level","Value","Console tag","Use for","Example"],[
["Trace","0","trce","Very detailed internals; never on in production","\"Parsed cell C7 = '456.00'\""],
["Debug","1","dbug","Developer diagnostics","\"Using data file /home/priya/.local/share/...\""],
["Information","2","info","Normal milestones of the app","\"Imported 1,240 orders in 84 ms\""],
["Warning","3","warn","Unexpected but handled; might need attention","\"Row 17 skipped: amount 'abc' is not a number\""],
["Error","4","fail","An operation failed; the app continues","\"Saving expenses failed\" + exception"],
["Critical","5","crit","The app can't continue or data is at risk","\"Data file corrupt; refusing to start\""],
["None","6","","Used only in filters to switch a category off",""]])}
{tip("A useful test for Warning vs Error: did the <i>current operation</i> fail? A skipped bad row is a Warning (the import still succeeded). A failed save is an Error.")}

<h3>4. Structured logging with message templates</h3>
{C(r"""
string orderId = "ORD-1042";
decimal amount = 2360m;

// ❌ Interpolation: the logger gets one finished string. No OrderId field, and the string
//    is built even when the level is filtered out.
log.LogInformation($"Order {orderId} paid {amount}");

// ✓ Template: the text and the values are kept separately
log.LogInformation("Order {OrderId} paid {Amount} via {PaymentMode}", orderId, amount, "UPI");

// Format specifiers work inside placeholders
log.LogInformation("GST for {OrderId} is {Gst:N2}", orderId, amount * 0.18m);

// Exceptions: always the FIRST argument, so providers record the type and stack trace
try
{
    decimal.Parse("₹2,360");
}
catch (FormatException ex)
{
    log.LogError(ex, "Could not parse amount {RawAmount} in row {Row}", "₹2,360", 17);
}

// EventIds: stable numbers for events you want to alert on
log.LogWarning(new EventId(4001, "DuplicateOrder"), "Duplicate order {OrderId} skipped", orderId);
""", "Structured.cs")}
<p>Switch to the JSON formatter to see the structure. Log tools such as Seq, Elastic, Application Insights and Loki store these fields as searchable data:</p>
{C(r"""
// builder.AddJsonConsole(o => o.JsonWriterOptions = new System.Text.Json.JsonWriterOptions { Indented = true });
""")}
{C(r"""
{
  "EventId": 0,
  "LogLevel": "Information",
  "Category": "Program",
  "Message": "Order ORD-1042 paid 2360 via UPI",
  "State": {
    "Message": "Order ORD-1042 paid 2360 via UPI",
    "OrderId": "ORD-1042",
    "Amount": 2360,
    "PaymentMode": "UPI",
    "{OriginalFormat}": "Order {OrderId} paid {Amount} via {PaymentMode}"
  }
}
""", "JSON console output (shape)", lang="json")}
{warn("Placeholders are matched by <b>position</b>: <code>LogInformation(\"{Amount} for {OrderId}\", orderId, amount)</code> stores the order ID under Amount. The name is only a label. Also keep personal data (full card numbers, Aadhaar, passwords, OTPs) out of logs. Log an ID or a masked value instead.", "Gotcha")}

<h3>5. Scopes: context for a block of work</h3>
{C(r"""
string[] files = ["orders_nov.csv", "orders_dec.csv"];
foreach (string file in files)
{
    using (log.BeginScope("File {FileName}", file))
    {
        log.LogInformation("Import started");
        for (int row = 1; row <= 2; row++)
        {
            using (log.BeginScope("Row {Row}", row))
            {
                log.LogDebug("Row parsed");
            }
        }
        log.LogInformation("Import finished");
    }
}
// With IncludeScopes = true the console output looks roughly like:
// 10:15:03 info: Program[0] => File orders_nov.csv Import started
// 10:15:03 dbug: Program[0] => File orders_nov.csv => Row 1 Row parsed
// 10:15:03 dbug: Program[0] => File orders_nov.csv => Row 2 Row parsed
// 10:15:03 info: Program[0] => File orders_nov.csv Import finished
""", "Scopes.cs")}
<p>In ASP.NET Core the framework opens a scope per request (with a RequestId and TraceId), so every log line from that request can be tied together. Structured providers store scope values as fields too (<code>FileName</code>, <code>Row</code>).</p>

<h3>6. Filtering, performance and the LoggerMessage generator</h3>
{C(r"""
using ILoggerFactory factory = LoggerFactory.Create(builder => builder
    .AddSimpleConsole(o => o.SingleLine = true)
    .SetMinimumLevel(LogLevel.Information)               // global floor
    .AddFilter("OrderImporter.Csv", LogLevel.Debug)      // a category you're debugging right now
    .AddFilter("System.Net.Http", LogLevel.Warning));    // a noisy library
""", "Filters.cs")}
<p>The same rules usually live in configuration (tomorrow), so you can change them without recompiling. The longest matching category prefix wins:</p>
{C(r"""
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "OrderImporter.Csv": "Debug",
      "Microsoft": "Warning"
    }
  }
}
""", "appsettings.json", lang="json")}
{C(r"""
// Skip building an expensive argument when the level is off
if (log.IsEnabled(LogLevel.Debug))
    log.LogDebug("Full order payload: {Payload}", System.Text.Json.JsonSerializer.Serialize(order));

// Call site of the generated methods below: strongly typed, no boxing, level check built in
Log.Imported(log, 1240, "orders_nov.csv", 84);

// High-performance logging (.NET 6+): the generator writes the method body for you
public static partial class Log
{
    [LoggerMessage(EventId = 2001, Level = LogLevel.Information,
                   Message = "Imported {Count} orders from {FileName} in {ElapsedMs} ms")]
    public static partial void Imported(ILogger logger, int count, string fileName, long elapsedMs);

    [LoggerMessage(EventId = 4001, Level = LogLevel.Warning, Message = "Row {Row} skipped: {Reason}")]
    public static partial void RowSkipped(ILogger logger, int row, string reason);
}
""", "LoggingPerformance.cs")}
{table(["Option","When"],[
["Plain <code>LogInformation(template, args)</code>","Most code; it's fine"],
["<code>IsEnabled</code> check","When an argument is expensive to compute"],
["<code>[LoggerMessage]</code> source generator","Hot paths (per request or per row), libraries, or when you want a catalogue of event IDs"],
["Serilog / NLog behind ILogger","When you need rolling files, many sinks or enrichers. Your code still uses ILogger"]])}
''',
["Using string interpolation in log calls, which loses structure and allocates even when the level is filtered out.",
"Passing the exception as a placeholder argument (<code>LogError(\"Failed {Ex}\", ex)</code>) instead of the first parameter.",
"Logging everything as Information, so real problems drown in noise.",
"Not disposing the LoggerFactory in a short console app, so the final messages never appear.",
"Logging secrets or personal data (passwords, OTPs, full card numbers, Aadhaar)."],
("35 min", ["Add logging to last week's grade analyser (or any earlier project): Information for start/finish with counts and elapsed ms, Warning for each skipped CSV row with the row number and reason, Error with the exception when the file can't be opened.",
"Wrap processing of each input file in a scope with the file name, turn on <code>IncludeScopes</code>, and process two files. Then switch to <code>AddJsonConsole</code> and look at the structured output.",
"Move the Warning and Information calls into a static partial <code>Log</code> class with <code>[LoggerMessage]</code> methods and EventIds 1000+. Add a filter that hides Information from your CSV category but keeps Warnings."]),
[("What's wrong with LogInformation($\"User {id} logged in\")?","The logger receives an already-formatted string. There's no structured UserId field, every message has a different template so tools can't group them, and the string is built even when Information is disabled."),
("What determines a logger's category?","The name you pass to CreateLogger(name), or the full type name for ILogger&lt;T&gt;. Filters match on category prefixes."),
("Why might the last log lines be missing when a console app exits?","The console provider queues messages and writes them on a background thread. If the app exits without disposing the LoggerFactory or host, queued messages may never be written.")],
[("Basic","Why use ILogger instead of Console.WriteLine?","ILogger gives levels, categories, filtering by config, structured data, exception details, scopes and pluggable destinations (console, files, cloud) without changing calling code. Console.WriteLine is unfiltered plain text that only goes to stdout."),
("Basic","Name the log levels in order and when you'd use each.","Trace (finest detail), Debug (developer diagnostics), Information (normal milestones), Warning (unexpected but handled), Error (an operation failed), Critical (app-wide failure or data at risk). None turns a category off in filters."),
("Basic","What is structured logging?","Logging with message templates whose placeholder values are kept as named properties rather than only merged into text. Log stores can then filter and aggregate by those fields, e.g. all Errors where OrderId = ORD-1042."),
("Intermediate","What are logging scopes and when would you use them?","BeginScope attaches context, such as a request ID, file name or order ID, to every log written inside the scope, including from deeper method calls that know nothing about it. ASP.NET Core opens one per request. Use them to correlate messages from one unit of work."),
("Intermediate","How do log filter rules work?","Each rule has an optional provider, a category prefix and a minimum level. For each message the most specific matching rule applies: the provider-specific rule first, then the longest matching category prefix, then Default. Rules come from code (AddFilter) or the Logging section of configuration."),
("Intermediate","What does the LoggerMessage source generator give you?","Compile-time generated logging methods. Templates are parsed once, IsEnabled is checked before any work, value types aren't boxed, and each event has a fixed EventId and a strongly typed signature. It's the recommended approach for hot paths and libraries.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Configuration in console apps and the Generic Host",
"Stop hard-coding file paths, limits and keys: layer appsettings.json, environment-specific files, environment variables and command-line arguments, bind them to strongly typed options classes, keep secrets out of git, and see how Host.CreateApplicationBuilder bundles config, logging and DI exactly like ASP.NET Core.",
[("Microsoft.Extensions.Configuration","The .NET configuration system: key/value settings collected from many providers into one view."),
("Configuration provider","A source of settings: JSON file, environment variables, command line, user secrets, Azure Key Vault…"),
("IConfiguration","The merged view. Read values with <code>config[\"Section:Key\"]</code>."),
("Configuration key","A path with colons for nesting: <code>Storage:DataFile</code>. Keys are case-insensitive."),
("Section","A subtree, <code>config.GetSection(\"Storage\")</code>, which is also an IConfiguration."),
("Layering / precedence","Providers added later override earlier ones for the same key."),
("Environment name","Development, Staging or Production. Set with <code>DOTNET_ENVIRONMENT</code> (or <code>ASPNETCORE_ENVIRONMENT</code> for web apps). The default is Production."),
("Binding","Copying a section's values into a C# object's properties: <code>section.Get&lt;T&gt;()</code> or <code>section.Bind(obj)</code>."),
("Options pattern","Registering settings classes in DI and consuming them as <code>IOptions&lt;T&gt;</code>, <code>IOptionsSnapshot&lt;T&gt;</code> or <code>IOptionsMonitor&lt;T&gt;</code>."),
("User secrets","A development-only JSON file stored in your user profile, outside the project folder, so secrets never get committed."),
("Generic Host","<code>IHost</code>: the object that wires up configuration, logging, dependency injection and app lifetime. ASP.NET Core is built on it."),
("HostApplicationBuilder",".NET 7+ builder from <code>Host.CreateApplicationBuilder(args)</code>, with sensible defaults already applied."),
("Dependency injection (DI)","The container creates your classes and passes in what their constructors ask for (covered in depth in Phase 2).")],
["Order matters: JSON → environment JSON → user secrets (Development) → environment variables → command line. The last one wins.",
"Environment variables use <code>__</code> (double underscore) where config keys use <code>:</code>.",
"Mark <code>appsettings.json</code> as <b>copy to output</b>, or it won't be found next to the .dll.",
"Bind sections to small options classes, and validate them at startup rather than on first use.",
"Never commit secrets. Use user secrets locally and environment variables or a vault in production.",
"Everything here works exactly the same in ASP.NET Core, which uses the same libraries."],
f'''
<h3>1. Building a configuration from providers</h3>
{C(r"""
dotnet new console -n GstInvoicer
cd GstInvoicer
dotnet add package Microsoft.Extensions.Configuration.Json
dotnet add package Microsoft.Extensions.Configuration.EnvironmentVariables
dotnet add package Microsoft.Extensions.Configuration.CommandLine
dotnet add package Microsoft.Extensions.Configuration.Binder
""", lang="bash")}
{C(r"""
{
  "Company": {
    "Name": "Sharma Stationers",
    "Gstin": "27ABCDE1234F1Z5",
    "State": "Maharashtra"
  },
  "Invoice": {
    "Prefix": "INV",
    "GstRatePercent": 18,
    "DueInDays": 15,
    "OutputFolder": "invoices"
  },
  "Smtp": {
    "Host": "smtp.example.com",
    "Port": 587,
    "User": "billing@example.com",
    "Password": ""
  }
}
""", "appsettings.json", lang="json")}
{C(r"""
<ItemGroup>
  <!-- copy appsettings.json and appsettings.*.json next to the .dll on build -->
  <None Update="appsettings*.json" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
""", "GstInvoicer.csproj (add)", lang="xml")}
{C(r"""
using Microsoft.Extensions.Configuration;

string environment = Environment.GetEnvironmentVariable("DOTNET_ENVIRONMENT") ?? "Production";

IConfiguration config = new ConfigurationBuilder()
    .SetBasePath(AppContext.BaseDirectory)                              // look next to the .dll
    .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
    .AddJsonFile($"appsettings.{environment}.json", optional: true)
    .AddEnvironmentVariables(prefix: "INVOICER_")                       // only INVOICER_* variables, prefix removed
    .AddCommandLine(args)
    .Build();

string company = config["Company:Name"] ?? "(not set)";
int dueDays = config.GetValue<int>("Invoice:DueInDays");               // 15
decimal gst = config.GetValue("Invoice:GstRatePercent", 18m);         // with a default
string? smtpHost = config.GetSection("Smtp")["Host"];

Console.WriteLine($"{company}: GST {gst}%, due in {dueDays} days ({environment})");
// Sharma Stationers: GST 18%, due in 15 days (Production)
""", "Program.cs")}

<h3>2. Environment-specific files</h3>
<p>Put only the <i>differences</i> in the environment file. Everything else comes from <code>appsettings.json</code>.</p>
{C(r"""
{
  "Invoice": {
    "DueInDays": 7,
    "OutputFolder": "invoices-dev"
  },
  "Smtp": {
    "Host": "localhost",
    "Port": 2525
  }
}
""", "appsettings.Development.json", lang="json")}
{C(r"""
dotnet run                                          # due in 15 days (appsettings.json)
DOTNET_ENVIRONMENT=Development dotnet run           # due in 7 days  (Development file overrides)

# Windows PowerShell
$env:DOTNET_ENVIRONMENT = "Development"; dotnet run
""", lang="bash")}

<h3>3. Environment variables and command-line arguments</h3>
{table(["Source","How you write Invoice:DueInDays = 30","Notes"],[
["JSON","<code>\"Invoice\": { \"DueInDays\": 30 }</code>","Nesting becomes <code>:</code>"],
["JSON array","<code>\"Categories\": [\"Food\", \"Rent\"]</code>","Keys <code>Categories:0</code>, <code>Categories:1</code>"],
["Environment variable","<code>INVOICER_Invoice__DueInDays=30</code>","<code>__</code> → <code>:</code>; the prefix is removed"],
["Command line","<code>--Invoice:DueInDays=30</code> or <code>--Invoice:DueInDays 30</code>","After <code>--</code> with dotnet run"],
["User secrets","<code>dotnet user-secrets set \"Invoice:DueInDays\" \"30\"</code>","Development only"]])}
{C(r"""
INVOICER_Invoice__DueInDays=30 dotnet run                                   # 30: env var beats JSON
INVOICER_Invoice__DueInDays=30 dotnet run -- --Invoice:DueInDays=45         # 45: command line beats everything
dotnet run -- --Smtp:Host smtp.office.example.com
""", lang="bash")}
{tip("Containers, Kubernetes and Azure App Service all configure apps through environment variables, which is why <code>__</code> exists: many shells and platforms don't allow <code>:</code> in variable names.")}

<h3>4. Binding to strongly typed options classes</h3>
<p>Reading <code>config[\"Invoice:DueInDays\"]</code> all over the code spreads magic strings around and parses values over and over. Bind each section once to a small class.</p>
{C(r"""
using System.ComponentModel.DataAnnotations;

public sealed class InvoiceOptions
{
    public const string SectionName = "Invoice";

    [Required, RegularExpression("^[A-Z]{2,5}$")]
    public string Prefix { get; set; } = "INV";

    [Range(typeof(decimal), "0", "28")]
    public decimal GstRatePercent { get; set; } = 18;

    [Range(1, 90)]
    public int DueInDays { get; set; } = 15;

    [Required]
    public string OutputFolder { get; set; } = "invoices";
}
""", "InvoiceOptions.cs")}
{C(r"""
using System.ComponentModel.DataAnnotations;

// Create and fill a new object (null if the section doesn't exist)
InvoiceOptions invoice = config.GetSection(InvoiceOptions.SectionName).Get<InvoiceOptions>() ?? new();

// Or fill an existing object; keys that are missing keep their defaults
var options = new InvoiceOptions();
config.GetSection(InvoiceOptions.SectionName).Bind(options);

// Validate without a host
var errors = new List<ValidationResult>();
if (!Validator.TryValidateObject(invoice, new ValidationContext(invoice), errors, validateAllProperties: true))
{
    Console.Error.WriteLine("Invalid configuration: " + string.Join("; ", errors.Select(e => e.ErrorMessage)));
    return 1;
}
Console.WriteLine($"{invoice.Prefix}, {invoice.GstRatePercent}% GST, {invoice.DueInDays} days");
return 0;
""", "Binding.cs")}
{warn("Binding is forgiving in some ways and strict in others. A misspelt key (<code>\"DueInDay\"</code>) is silently ignored and the default stays. A value that can't be converted (<code>\"DueInDays\": \"fifteen\"</code>) throws InvalidOperationException. Validation catches the first kind of problem.", "Gotcha")}

<h3>5. User secrets (awareness)</h3>
{C(r"""
dotnet user-secrets init                                   # adds <UserSecretsId> to the .csproj
dotnet user-secrets set "Smtp:Password" "dev-only-password"
dotnet user-secrets list
# Stored OUTSIDE the project:
#   Windows: %APPDATA%\Microsoft\UserSecrets\<id>\secrets.json
#   Linux/macOS: ~/.microsoft/usersecrets/<id>/secrets.json
""", lang="bash")}
{C(r"""
// dotnet add package Microsoft.Extensions.Configuration.UserSecrets
var builder = new ConfigurationBuilder()
    .AddJsonFile("appsettings.json", optional: false)
    .AddUserSecrets<Program>(optional: true)    // usually only in Development
    .AddEnvironmentVariables(prefix: "INVOICER_");
""")}
<p>User secrets are <b>not encrypted</b>. They just keep secrets out of your repository. In production, use environment variables set by the platform or a vault such as Azure Key Vault (Phase 4).</p>

<h3>6. The Generic Host: config + logging + DI in one line</h3>
<p>Everything you wired by hand this week (configuration layers, logging, filters) is exactly what <code>Host.CreateApplicationBuilder</code> sets up for you. ASP.NET Core's <code>WebApplication.CreateBuilder</code> is the same idea with a web server added, so this is your bridge to Phase 2.</p>
{C(r"""
dotnet add package Microsoft.Extensions.Hosting
dotnet add package Microsoft.Extensions.Options.DataAnnotations
""", lang="bash")}
{C(r"""
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

HostApplicationBuilder builder = Host.CreateApplicationBuilder(args);   // .NET 7+
// Already done for you:
//   appsettings.json, appsettings.{Environment}.json, user secrets (Development),
//   environment variables, command line, console + debug logging with the "Logging" section, DI container

builder.Services.AddOptions<InvoiceOptions>()
    .Bind(builder.Configuration.GetSection(InvoiceOptions.SectionName))
    .ValidateDataAnnotations()
    .ValidateOnStart();                           // checked when the host starts
builder.Services.AddSingleton<InvoiceNumberer>();

using IHost host = builder.Build();

var numberer = host.Services.GetRequiredService<InvoiceNumberer>();   // DI creates it with its dependencies
Console.WriteLine(numberer.Next());   // INV-2026-0001
Console.WriteLine(numberer.Next());   // INV-2026-0002
Console.WriteLine(host.Services.GetRequiredService<IHostEnvironment>().EnvironmentName);   // Production

public sealed class InvoiceNumberer(IOptions<InvoiceOptions> options, ILogger<InvoiceNumberer> logger)
{
    private int _next = 1;

    public string Next()
    {
        string number = $"{options.Value.Prefix}-{DateTime.Today.Year}-{_next++:D4}";
        logger.LogInformation("Issued invoice number {InvoiceNumber}", number);
        return number;
    }
}
""", "Program.cs (Generic Host)")}
{warn("<code>ValidateOnStart</code> runs when the host <b>starts</b> (<code>host.Run()</code> / <code>StartAsync</code>). In an interactive console app that only calls <code>Build()</code> and resolves services, validation happens the first time something reads <code>options.Value</code>, which throws OptionsValidationException. Also note that the host's content root is the <b>current directory</b> by default. Saturday's project sets it to <code>AppContext.BaseDirectory</code> so appsettings.json is found wherever the app is run from.", "Console apps")}
{table(["Interface","Lifetime","Sees config changes?","Use in"],[
["<code>IOptions&lt;T&gt;</code>","Singleton, read once","No","Most console apps and singletons"],
["<code>IOptionsSnapshot&lt;T&gt;</code>","Scoped, re-read per scope (per web request)","Yes, next scope","Scoped services in web apps"],
["<code>IOptionsMonitor&lt;T&gt;</code>","Singleton with <code>CurrentValue</code> and <code>OnChange</code>","Yes, immediately","Long-running services, feature flags"]])}
''',
["<code>appsettings.json</code> not copied to the output folder, so the app silently runs on defaults (or fails when the file is required).",
"Using <code>:</code> in environment variable names on Linux, or forgetting the prefix, so the override never applies.",
"Committing real passwords or API keys in <code>appsettings.json</code>.",
"Reading <code>config[\"Some:Key\"]</code> in dozens of places instead of binding once to an options class.",
"Assuming <code>ValidateOnStart</code> ran when the host was never started."],
("40 min", ["Create <code>appsettings.json</code> and <code>appsettings.Development.json</code> for the invoicer above. Print the effective <code>InvoiceOptions</code> under Production, Development, with an <code>INVOICER_Invoice__DueInDays</code> environment variable, and with a command-line override. Write down which source won each time.",
"Add DataAnnotations to <code>InvoiceOptions</code> and make startup fail with a clear message when <code>GstRatePercent</code> is 35 or <code>Prefix</code> is lowercase.",
"Rewrite the program with <code>Host.CreateApplicationBuilder</code>: register InvoiceOptions with validation, inject <code>ILogger&lt;T&gt;</code> and <code>IOptions&lt;InvoiceOptions&gt;</code> into an <code>InvoiceService</code>, and set the console log level for your namespace to Debug through configuration only."]),
[("If appsettings.json sets DueInDays to 15 and the environment variable INVOICER_Invoice__DueInDays is 30, which wins?","30, assuming AddEnvironmentVariables(\"INVOICER_\") was added after the JSON file. Later providers override earlier ones."),
("How do you represent the key Storage:DataFile in an environment variable?","Storage__DataFile (double underscore for each colon), plus any prefix your app configured, e.g. EXPENSES_Storage__DataFile."),
("What does Host.CreateApplicationBuilder add that ConfigurationBuilder doesn't?","Default configuration sources (including environment files and user secrets in Development), logging configured from the Logging section, a DI container, the hosting environment and application lifetime management.")],
[("Basic","How does configuration precedence work in .NET?","Providers are added in order and later ones override earlier ones for the same key. The default host order is appsettings.json, appsettings.{Environment}.json, user secrets (Development only), environment variables, then command-line arguments."),
("Basic","What is the options pattern?","Binding a configuration section to a strongly typed class and consuming it through IOptions&lt;T&gt; (or Snapshot/Monitor) via DI. It removes magic strings, gives type conversion and validation, and keeps each class depending only on the settings it needs."),
("Basic","How should you store secrets for local development and production?","Locally use user secrets (dotnet user-secrets), which live outside the repo. In production use environment variables injected by the platform, or a secret store such as Azure Key Vault, often with a managed identity. Never commit them to appsettings.json."),
("Intermediate","IOptions vs IOptionsSnapshot vs IOptionsMonitor?","IOptions is a singleton computed once, so it ignores later changes. IOptionsSnapshot is scoped and recomputed per scope (per request), so it picks up reloaded config and can't be injected into singletons. IOptionsMonitor is a singleton that exposes CurrentValue and an OnChange callback for live updates."),
("Intermediate","How do you validate configuration at startup?","AddOptions&lt;T&gt;().Bind(section).ValidateDataAnnotations() (or .Validate(predicate) / IValidateOptions&lt;T&gt;), then .ValidateOnStart() so the host fails fast when it starts instead of on first use. Without a host, call Validator.TryValidateObject yourself after binding."),
("Intermediate","What is the Generic Host and why use it in a console app?","IHost wires configuration, logging, DI and lifetime (graceful shutdown on Ctrl+C) in the same way as ASP.NET Core. It's worth it for anything beyond a toy: background workers (BackgroundService), apps with several services, or code you'll later move into a web API.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project 4: Expense tracker with JSON storage",
"Build a console expense tracker that stores data in a JSON file: an immutable Expense record, an IExpenseStore abstraction with a JSON implementation that saves atomically, add/list/edit/delete, the data path from configuration, and ILogger throughout. Budget: about 4 hours.",
[("Persistence","Keeping data after the program exits, here in a JSON file."),
("Atomic save","A write that either fully replaces the old file or leaves it untouched. It never leaves a half-written file."),
("Temp file + replace","Write the new content to <code>expenses.json.tmp</code>, then swap it into place in one rename-style step."),
("Schema version","A number stored in the file so future versions of the app know how to read old data."),
("Store abstraction","<code>IExpenseStore</code>: the rest of the app doesn't know (or care) that data lives in JSON.")],
["Expense is an immutable positional record; edits use <code>with</code>.",
"The JSON file wraps the list in an object with a <code>version</code> field.",
"Saves go to a temp file, which then replaces the real file and keeps a <code>.bak</code> of the previous version.",
"The service saves <b>first</b> and updates memory only if the save succeeded.",
"A corrupt data file stops the app at startup. It never silently starts empty and overwrites your data.",
"Tomorrow adds monthly LINQ reports, budget alerts from config and CSV export."],
f'''
<h3>Requirements</h3>
<ul>
<li><b>Expense</b>: Id, Date, Category (Food, Groceries, Rent, Transport, Utilities, Shopping, Health, Entertainment, Education, Other), Amount (₹, decimal, up to 2 places, max ₹10 lakh), PaymentMode (UPI, Card, Cash), optional Note (≤ 200 characters).</li>
<li>Menu: list, add, edit, delete, exit. Each change is saved immediately.</li>
<li>Storage: one JSON file, camelCase, indented, enums as strings, ₹ kept readable. Its location comes from configuration (<code>Storage:DataFile</code>) and can be overridden by environment variable or command line.</li>
<li>Saving is atomic, and the previous version is kept as <code>.bak</code>.</li>
<li>Missing file → start empty. Corrupt file → refuse to start, with a clear message and the line number.</li>
<li>ILogger for every load, save and change; the console stays readable (Warning by default, Information for our namespace).</li>
</ul>

<h3>Scaffold</h3>
{C(r"""
dotnet new sln -n ExpenseTracker
dotnet new classlib -n ExpenseTracker.Core
dotnet new console  -n ExpenseTracker.App
dotnet sln add ExpenseTracker.Core ExpenseTracker.App
dotnet add ExpenseTracker.App reference ExpenseTracker.Core
rm ExpenseTracker.Core/Class1.cs

dotnet add ExpenseTracker.Core package Microsoft.Extensions.Logging.Abstractions
dotnet add ExpenseTracker.Core package Microsoft.Extensions.Options
dotnet add ExpenseTracker.App  package Microsoft.Extensions.Hosting
dotnet new gitignore
""", lang="bash")}
{C(r"""
ExpenseTracker/
├─ ExpenseTracker.sln
├─ .gitignore
├─ ExpenseTracker.Core/
│  ├─ Models/
│  │  ├─ Category.cs
│  │  ├─ PaymentMode.cs
│  │  └─ Expense.cs
│  ├─ Storage/
│  │  ├─ IExpenseStore.cs
│  │  ├─ StorageOptions.cs
│  │  ├─ ExpenseStoreException.cs
│  │  ├─ ExpenseDocument.cs
│  │  └─ JsonFileExpenseStore.cs
│  └─ Services/
│     └─ ExpenseService.cs
└─ ExpenseTracker.App/
   ├─ appsettings.json
   ├─ ConsoleInput.cs
   └─ Program.cs
""", lang="text")}
<p>The Core library references only the logging and options <i>abstractions</i>. It doesn't know about the console or about the host. Only the App references <code>Microsoft.Extensions.Hosting</code>.</p>

<h3>Step 1 — Enums and the Expense record</h3>
{C(r"""
namespace ExpenseTracker.Core.Models;

// Start at 1 so a missing value (0) is detectable
public enum Category
{
    Food = 1, Groceries, Rent, Transport, Utilities, Shopping, Health, Entertainment, Education, Other
}

public enum PaymentMode
{
    Upi = 1, Card, Cash
}
""", "ExpenseTracker.Core/Models/Category.cs + PaymentMode.cs")}
{C(r"""
namespace ExpenseTracker.Core.Models;

public sealed record Expense(
    int Id,
    DateOnly Date,
    Category Category,
    decimal Amount,
    PaymentMode PaymentMode,
    string? Note = null)
{
    public const decimal MaxAmount = 10_00_000m;    // ₹10 lakh: anything bigger is almost certainly a typo
    public const int MaxNoteLength = 200;

    // Lazy list of problems (Week 4's yield); empty means valid
    public IEnumerable<string> Validate()
    {
        if (Id <= 0)
            yield return "Id must be positive";
        if (Date < new DateOnly(2000, 1, 1) || Date > DateOnly.FromDateTime(DateTime.Today).AddDays(1))
            yield return $"Date {Date:yyyy-MM-dd} is out of range";
        if (!Enum.IsDefined(Category))
            yield return $"Unknown category {(int)Category}";
        if (!Enum.IsDefined(PaymentMode))
            yield return $"Unknown payment mode {(int)PaymentMode}";
        if (Amount <= 0 || Amount > MaxAmount)
            yield return $"Amount must be between ₹0.01 and ₹{MaxAmount:N0}";
        if (decimal.Round(Amount, 2) != Amount)
            yield return "Amount can have at most 2 decimal places";
        if (Note is { Length: > MaxNoteLength })
            yield return $"Note is longer than {MaxNoteLength} characters";
    }
}
""", "ExpenseTracker.Core/Models/Expense.cs")}

<h3>Step 2 — The store abstraction, options and exception</h3>
{C(r"""
using ExpenseTracker.Core.Models;

namespace ExpenseTracker.Core.Storage;

public interface IExpenseStore
{
    /// <summary>Where the data lives (a file path for the JSON store).</summary>
    string Location { get; }

    Task<IReadOnlyList<Expense>> LoadAsync(CancellationToken ct = default);

    /// <summary>Replaces ALL stored expenses with <paramref name="expenses"/>.</summary>
    Task SaveAsync(IReadOnlyList<Expense> expenses, CancellationToken ct = default);
}
""", "ExpenseTracker.Core/Storage/IExpenseStore.cs")}
{C(r"""
namespace ExpenseTracker.Core.Storage;

public sealed class StorageOptions
{
    public const string SectionName = "Storage";

    /// <summary>Absolute path, or a path relative to LocalApplicationData/ExpenseTracker.</summary>
    public string DataFile { get; set; } = "expenses.json";
}

public sealed class ExpenseStoreException(string message, Exception? inner = null) : Exception(message, inner);
""", "ExpenseTracker.Core/Storage/StorageOptions.cs + ExpenseStoreException.cs")}
{C(r"""
using ExpenseTracker.Core.Models;

namespace ExpenseTracker.Core.Storage;

// The file's top-level shape: { "version": 1, "expenses": [ ... ] }
public sealed record ExpenseDocument(int Version, List<Expense> Expenses);
""", "ExpenseTracker.Core/Storage/ExpenseDocument.cs")}

<h3>Step 3 — JsonFileExpenseStore with atomic save</h3>
{C(r"""
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Unicode;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using ExpenseTracker.Core.Models;

namespace ExpenseTracker.Core.Storage;

public sealed class JsonFileExpenseStore : IExpenseStore
{
    public const int CurrentVersion = 1;

    // Created once and shared (Tuesday)
    internal static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,             // tolerate hand edits like "Amount"
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Converters = { new JsonStringEnumConverter() },
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
    };

    private readonly ILogger<JsonFileExpenseStore> _logger;

    public string Location { get; }

    public JsonFileExpenseStore(IOptions<StorageOptions> options, ILogger<JsonFileExpenseStore> logger)
    {
        _logger = logger;
        string configured = options.Value.DataFile;
        if (string.IsNullOrWhiteSpace(configured))
            throw new ExpenseStoreException("Storage:DataFile is empty in configuration");

        // Relative paths go under the user's app-data folder, not wherever the app was launched from (Monday)
        string baseDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ExpenseTracker");
        Location = Path.GetFullPath(Path.IsPathRooted(configured) ? configured : Path.Combine(baseDir, configured));
        _logger.LogDebug("Expense data file resolved to {Path}", Location);
    }

    public async Task<IReadOnlyList<Expense>> LoadAsync(CancellationToken ct = default)
    {
        if (!File.Exists(Location))
        {
            _logger.LogInformation("No data file at {Path}; starting with an empty list", Location);
            return [];
        }

        try
        {
            await using var stream = new FileStream(Location, FileMode.Open, FileAccess.Read, FileShare.Read,
                                                    bufferSize: 4096, useAsync: true);
            ExpenseDocument doc = await JsonSerializer.DeserializeAsync<ExpenseDocument>(stream, JsonOptions, ct)
                ?? throw new ExpenseStoreException($"{Location} contains 'null' instead of expense data");

            if (doc.Version > CurrentVersion)
                throw new ExpenseStoreException(
                    $"{Location} was written by a newer version (v{doc.Version}); this app understands v{CurrentVersion}");

            List<Expense> expenses = doc.Expenses ?? [];
            _logger.LogInformation("Loaded {Count} expenses from {Path}", expenses.Count, Location);
            return expenses;
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "Data file {Path} is not valid JSON (line {Line}, byte {Position})",
                             Location, ex.LineNumber + 1, ex.BytePositionInLine);
            throw new ExpenseStoreException(
                $"{Location} is corrupt near line {ex.LineNumber + 1}. Fix it, or restore {Location}.bak", ex);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            _logger.LogError(ex, "Could not read {Path}", Location);
            throw new ExpenseStoreException($"Could not read {Location}: {ex.Message}", ex);
        }
    }

    public async Task SaveAsync(IReadOnlyList<Expense> expenses, CancellationToken ct = default)
    {
        string tempPath = Location + ".tmp";
        string backupPath = Location + ".bak";
        var doc = new ExpenseDocument(CurrentVersion, expenses.OrderBy(e => e.Date).ThenBy(e => e.Id).ToList());

        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Location)!);

            // 1. Write the complete new content to a temp file in the SAME folder
            await using (var stream = new FileStream(tempPath, FileMode.Create, FileAccess.Write, FileShare.None,
                                                     bufferSize: 4096, useAsync: true))
            {
                await JsonSerializer.SerializeAsync(stream, doc, JsonOptions, ct);
                stream.Flush(flushToDisk: true);      // make sure the bytes are on disk before we swap
            }

            // 2. Swap it in. Replace keeps the old file as .bak; Move is used for the very first save
            if (File.Exists(Location))
                File.Replace(tempPath, Location, backupPath);
            else
                File.Move(tempPath, Location);

            _logger.LogInformation("Saved {Count} expenses to {Path}", doc.Expenses.Count, Location);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            _logger.LogError(ex, "Saving to {Path} failed", Location);
            TryDelete(tempPath);
            throw new ExpenseStoreException($"Could not save to {Location}: {ex.Message}", ex);
        }
    }

    private void TryDelete(string path)
    {
        try { File.Delete(path); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            _logger.LogWarning(ex, "Could not delete temp file {Path}", path);
        }
    }
}
""", "ExpenseTracker.Core/Storage/JsonFileExpenseStore.cs")}
<h4>Why temp file + replace?</h4>
{table(["Approach","If the app crashes or the disk fills mid-write"],[
["<code>File.WriteAllText(path, json)</code>","The file is truncated first, so a crash leaves it half-written or empty and all data is lost"],
["Write <code>.tmp</code>, then <code>File.Replace</code>","The real file is untouched until the swap. The swap is a rename on the same volume (Linux/macOS) or ReplaceFile (Windows), so readers see either the old file or the new one"]])}
<p>On Linux and macOS the swap is a true atomic rename. On Windows, <code>ReplaceFile</code> is about as close as the OS offers. Either way the temp file must be in the same folder, because a rename across volumes becomes a copy.</p>

<h3>Step 4 — ExpenseService</h3>
{C(r"""
using ExpenseTracker.Core.Models;
using ExpenseTracker.Core.Storage;
using Microsoft.Extensions.Logging;

namespace ExpenseTracker.Core.Services;

public sealed class ExpenseService(IExpenseStore store, ILogger<ExpenseService> logger)
{
    private List<Expense> _expenses = [];
    private bool _loaded;

    public IReadOnlyList<Expense> All => _expenses;

    public async Task LoadAsync(CancellationToken ct = default)
    {
        _expenses = (await store.LoadAsync(ct)).ToList();
        _loaded = true;

        var invalidIds = _expenses.Where(e => e.Validate().Any()).Select(e => e.Id).ToList();
        if (invalidIds.Count > 0)
            logger.LogWarning("{Count} stored expenses failed validation (ids: {Ids})",
                              invalidIds.Count, string.Join(", ", invalidIds));

        int duplicateIds = _expenses.Count - _expenses.Select(e => e.Id).Distinct().Count();
        if (duplicateIds > 0)
            logger.LogWarning("{Count} duplicate expense ids found in {Path}", duplicateIds, store.Location);
    }

    public Expense? Find(int id) => _expenses.Find(e => e.Id == id);

    public async Task<Expense> AddAsync(DateOnly date, Category category, decimal amount,
                                        PaymentMode mode, string? note, CancellationToken ct = default)
    {
        EnsureLoaded();
        int nextId = _expenses.Count == 0 ? 1 : _expenses.Max(e => e.Id) + 1;
        var expense = new Expense(nextId, date, category, amount, mode, Clean(note));
        ThrowIfInvalid(expense);

        await CommitAsync([.. _expenses, expense], ct);
        logger.LogInformation("Added expense {ExpenseId}: {Category} {Amount} via {PaymentMode}",
                              expense.Id, category, amount, mode);
        return expense;
    }

    public async Task<Expense> UpdateAsync(int id, Func<Expense, Expense> change, CancellationToken ct = default)
    {
        EnsureLoaded();
        Expense existing = Find(id) ?? throw new KeyNotFoundException($"No expense with id {id}");
        Expense changed = change(existing);
        Expense updated = changed with { Id = id, Note = Clean(changed.Note) };   // the id can't be changed
        ThrowIfInvalid(updated);
        if (updated == existing) return existing;                                  // record equality: nothing to save

        await CommitAsync(_expenses.Select(e => e.Id == id ? updated : e).ToList(), ct);
        logger.LogInformation("Updated expense {ExpenseId}: {Before} -> {After}", id, existing, updated);
        return updated;
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken ct = default)
    {
        EnsureLoaded();
        if (Find(id) is null) return false;

        await CommitAsync(_expenses.Where(e => e.Id != id).ToList(), ct);
        logger.LogInformation("Deleted expense {ExpenseId}", id);
        return true;
    }

    // Save FIRST, then swap the in-memory list: if the save throws, memory and disk still agree
    private async Task CommitAsync(List<Expense> next, CancellationToken ct)
    {
        await store.SaveAsync(next, ct);
        _expenses = next;
    }

    private void EnsureLoaded()
    {
        if (!_loaded) throw new InvalidOperationException("Call LoadAsync before changing expenses");
    }

    private static string? Clean(string? note) => string.IsNullOrWhiteSpace(note) ? null : note.Trim();

    private static void ThrowIfInvalid(Expense expense)
    {
        var errors = expense.Validate().ToList();
        if (errors.Count > 0) throw new ArgumentException(string.Join("; ", errors));
    }
}
""", "ExpenseTracker.Core/Services/ExpenseService.cs")}

<h3>Step 5 — Configuration</h3>
{C(r"""
{
  "Storage": {
    "DataFile": "expenses.json"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Warning",
      "ExpenseTracker": "Information"
    },
    "Console": {
      "FormatterName": "simple",
      "FormatterOptions": {
        "SingleLine": true,
        "TimestampFormat": "HH:mm:ss "
      }
    }
  }
}
""", "ExpenseTracker.App/appsettings.json", lang="json")}
{C(r"""
<ItemGroup>
  <None Update="appsettings*.json" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
""", "ExpenseTracker.App/ExpenseTracker.App.csproj (add)", lang="xml")}

<h3>Step 6 — ConsoleInput and display helpers</h3>
{C(r"""
using System.Globalization;
using ExpenseTracker.Core.Models;

namespace ExpenseTracker.App;

public static class ConsoleInput
{
    private static readonly string[] DateFormats = ["yyyy-MM-dd", "dd-MM-yyyy", "dd/MM/yyyy"];

    private static string ReadLine() =>
        Console.ReadLine() ?? throw new OperationCanceledException("Input was closed");

    public static string? ReadOptional(string prompt)
    {
        Console.Write(prompt);
        string line = ReadLine().Trim();
        return line.Length == 0 ? null : line;
    }

    public static int ReadInt(string prompt, int min, int max)
    {
        while (true)
        {
            Console.Write(prompt);
            if (int.TryParse(ReadLine(), out int value) && value >= min && value <= max) return value;
            Console.WriteLine($"  Enter a whole number from {min} to {max}.");
        }
    }

    public static decimal ReadAmount(string prompt)
    {
        while (true)
        {
            Console.Write(prompt);
            if (TryParseAmount(ReadLine(), out decimal amount)) return amount;
            Console.WriteLine("  Enter a positive amount, e.g. 249.50 or 1,200");
        }
    }

    public static bool TryParseAmount(string? text, out decimal amount)
    {
        string cleaned = (text ?? "").Replace("₹", "").Replace(",", "").Trim();
        return decimal.TryParse(cleaned, NumberStyles.Number, CultureInfo.InvariantCulture, out amount) && amount > 0;
    }

    public static DateOnly ReadDate(string prompt, DateOnly defaultValue)
    {
        while (true)
        {
            Console.Write(prompt);
            string text = ReadLine().Trim();
            if (text.Length == 0) return defaultValue;
            if (DateOnly.TryParseExact(text, DateFormats, CultureInfo.InvariantCulture, DateTimeStyles.None, out var date))
                return date;
            Console.WriteLine("  Use yyyy-MM-dd or dd-MM-yyyy.");
        }
    }

    public static T ReadEnum<T>(string label) where T : struct, Enum
    {
        T[] values = Enum.GetValues<T>();
        Console.WriteLine($"  {label}: " + string.Join("  ", values.Select((v, i) => $"{i + 1}) {v}")));
        int pick = ReadInt("  Choose: ", 1, values.Length);
        return values[pick - 1];
    }

    public static bool Confirm(string prompt) => ReadOptional(prompt + " (y/N): ") is "y" or "Y";
}

public static class Display
{
    private static readonly CultureInfo India = CultureInfo.GetCultureInfo("en-IN");

    public static string Rupees(decimal amount) => "₹" + amount.ToString("N2", India);   // ₹1,00,000.00
    public static string Mode(PaymentMode mode) => mode == PaymentMode.Upi ? "UPI" : mode.ToString();
}
""", "ExpenseTracker.App/ConsoleInput.cs")}

<h3>Step 7 — Program.cs with the Generic Host</h3>
{C(r"""
using System.Text;
using ExpenseTracker.App;
using ExpenseTracker.Core.Models;
using ExpenseTracker.Core.Services;
using ExpenseTracker.Core.Storage;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

Console.OutputEncoding = Encoding.UTF8;               // ₹ in the Windows console

var builder = Host.CreateApplicationBuilder(new HostApplicationBuilderSettings
{
    Args = args,
    ContentRootPath = AppContext.BaseDirectory        // find appsettings.json next to the .dll
});
builder.Services.Configure<StorageOptions>(builder.Configuration.GetSection(StorageOptions.SectionName));
builder.Services.AddSingleton<IExpenseStore, JsonFileExpenseStore>();
builder.Services.AddSingleton<ExpenseService>();

using IHost host = builder.Build();                   // disposing the host flushes the console logger
var log = host.Services.GetRequiredService<ILogger<Program>>();
var store = host.Services.GetRequiredService<IExpenseStore>();
var expenses = host.Services.GetRequiredService<ExpenseService>();

try
{
    await expenses.LoadAsync();
}
catch (ExpenseStoreException ex)
{
    log.LogCritical(ex, "Startup aborted: data file unusable");
    Console.WriteLine($"✗ {ex.Message}");
    Console.WriteLine("  Nothing was changed. Fix the file or restore the .bak copy, then run again.");
    return 1;
}

Console.WriteLine($"Expense Tracker · data file: {store.Location}");

int choice;
do
{
    Console.WriteLine(QQQ

        ===== Expense Tracker =====
        1) List expenses     3) Edit expense
        2) Add expense       4) Delete expense
        0) Exit
        QQQ);
    choice = ConsoleInput.ReadInt("Choose: ", 0, 4);

    try
    {
        switch (choice)
        {
            case 1: ListExpenses(expenses.All); break;
            case 2: await AddAsync(); break;
            case 3: await EditAsync(); break;
            case 4: await DeleteAsync(); break;
        }
    }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException)
    {
        Console.WriteLine($"  ✗ {ex.Message}");
    }
    catch (ExpenseStoreException ex)
    {
        Console.WriteLine($"  ✗ Not saved: {ex.Message}");
        Console.WriteLine("    Your data is unchanged.");
    }
} while (choice != 0);

return 0;

void ListExpenses(IEnumerable<Expense> list)
{
    var rows = list.OrderBy(e => e.Date).ThenBy(e => e.Id).ToList();
    if (rows.Count == 0)
    {
        Console.WriteLine("  (no expenses yet)");
        return;
    }

    Console.WriteLine($"  {"Id",4}  {"Date",-11} {"Category",-13} {"Mode",-5} {"Amount",14}  Note");
    foreach (var e in rows)
        Console.WriteLine($"  {e.Id,4}  {e.Date,-11:dd MMM yyyy} {e.Category,-13} {Display.Mode(e.PaymentMode),-5} {Display.Rupees(e.Amount),14}  {e.Note}");
    Console.WriteLine($"  {rows.Count} expenses, total {Display.Rupees(rows.Sum(e => e.Amount))}");
}

async Task AddAsync()
{
    DateOnly date = ConsoleInput.ReadDate("Date (yyyy-MM-dd, Enter = today): ", DateOnly.FromDateTime(DateTime.Today));
    Category category = ConsoleInput.ReadEnum<Category>("Category");
    decimal amount = ConsoleInput.ReadAmount("Amount ₹: ");
    PaymentMode mode = ConsoleInput.ReadEnum<PaymentMode>("Paid by");
    string? note = ConsoleInput.ReadOptional("Note (optional): ");

    Expense added = await expenses.AddAsync(date, category, amount, mode, note);
    Console.WriteLine($"  ✓ Saved #{added.Id}: {added.Category} {Display.Rupees(added.Amount)}");
}

async Task EditAsync()
{
    int id = ConsoleInput.ReadInt("Expense id: ", 1, int.MaxValue);
    Expense current = expenses.Find(id) ?? throw new KeyNotFoundException($"No expense with id {id}");
    Console.WriteLine($"  Editing #{id}. Press Enter to keep the current value.");

    string? amountText = ConsoleInput.ReadOptional($"  Amount [{current.Amount}]: ");
    decimal? newAmount = null;
    if (amountText is not null)
        newAmount = ConsoleInput.TryParseAmount(amountText, out decimal a) ? a : throw new ArgumentException($"'{amountText}' is not a valid amount");

    Category? newCategory = ConsoleInput.Confirm($"  Change category from {current.Category}?")
        ? ConsoleInput.ReadEnum<Category>("New category")
        : null;
    string? newNote = ConsoleInput.ReadOptional($"  Note [{current.Note}]: ");

    Expense updated = await expenses.UpdateAsync(id, e => e with
    {
        Amount = newAmount ?? e.Amount,
        Category = newCategory ?? e.Category,
        Note = newNote ?? e.Note
    });
    Console.WriteLine($"  ✓ #{updated.Id} is now {updated.Category} {Display.Rupees(updated.Amount)}");
}

async Task DeleteAsync()
{
    int id = ConsoleInput.ReadInt("Expense id: ", 1, int.MaxValue);
    if (expenses.Find(id) is not { } e) throw new KeyNotFoundException($"No expense with id {id}");
    if (!ConsoleInput.Confirm($"  Delete #{id} {e.Category} {Display.Rupees(e.Amount)}?")) return;

    bool removed = await expenses.DeleteAsync(id);
    Console.WriteLine(removed ? $"  ✓ Deleted #{id}" : $"  ✗ #{id} was already gone");
}
""", "ExpenseTracker.App/Program.cs")}
<p>Two notes on the host. First, <code>ILogger&lt;Program&gt;</code> works because top-level statements compile into a class called <code>Program</code>. Second, this app never calls <code>host.Run()</code>, because it's an interactive loop rather than a background service. We only use the host to build configuration, logging and DI.</p>

<h3>Run it</h3>
{C(r"""
dotnet run --project ExpenseTracker.App
""", lang="bash")}
{C(r"""
11:02:14 info: ExpenseTracker.Core.Storage.JsonFileExpenseStore[0] No data file at /home/priya/.local/share/ExpenseTracker/expenses.json; starting with an empty list
Expense Tracker · data file: /home/priya/.local/share/ExpenseTracker/expenses.json

===== Expense Tracker =====
1) List expenses     3) Edit expense
2) Add expense       4) Delete expense
0) Exit
Choose: 2
Date (yyyy-MM-dd, Enter = today): 2026-11-03
  Category: 1) Food  2) Groceries  3) Rent  4) Transport  5) Utilities  6) Shopping  7) Health  8) Entertainment  9) Education  10) Other
  Choose: 2
Amount ₹: 1,249.75
  Paid by: 1) Upi  2) Card  3) Cash
  Choose: 1
Note (optional): BigBasket weekly order
11:02:41 info: ExpenseTracker.Core.Storage.JsonFileExpenseStore[0] Saved 1 expenses to /home/priya/.local/share/ExpenseTracker/expenses.json
11:02:41 info: ExpenseTracker.Core.Services.ExpenseService[0] Added expense 1: Groceries 1249.75 via Upi
  ✓ Saved #1: Groceries ₹1,249.75
...
Choose: 1
    Id  Date        Category      Mode          Amount  Note
     1  03 Nov 2026 Groceries     UPI        ₹1,249.75  BigBasket weekly order
     2  05 Nov 2026 Rent          UPI       ₹18,500.00  November rent
     3  07 Nov 2026 Food          Cash         ₹240.00  Chai and samosa, office
  3 expenses, total ₹19,989.75
""", lang="text")}
<p class="muted">The console logger writes on a background thread, so a log line can sometimes appear just after the next prompt. That's expected. Tomorrow you'll lower the console level for a quieter UI.</p>
{C(r"""
{
  "version": 1,
  "expenses": [
    {
      "id": 1,
      "date": "2026-11-03",
      "category": "Groceries",
      "amount": 1249.75,
      "paymentMode": "Upi",
      "note": "BigBasket weekly order"
    },
    {
      "id": 2,
      "date": "2026-11-05",
      "category": "Rent",
      "amount": 18500,
      "paymentMode": "Upi",
      "note": "November rent"
    }
  ]
}
""", "~/.local/share/ExpenseTracker/expenses.json", lang="json")}
{C(r"""
# Point it at a different file without touching code
Storage__DataFile=/tmp/test-expenses.json dotnet run --project ExpenseTracker.App
dotnet run --project ExpenseTracker.App -- --Storage:DataFile=./demo.json
""", lang="bash")}

<h3>Stretch goals</h3>
<ul>
<li>Write an <code>InMemoryExpenseStore</code> (a List behind the interface) and use it to exercise <code>ExpenseService</code> without touching the disk. This is the start of Week 10's unit tests.</li>
<li>Store <code>nextId</code> in <code>ExpenseDocument</code> so ids aren't reused after you delete the newest expense.</li>
<li>Add a search option: by note text (case-insensitive), by category, or by date range.</li>
<li>.NET 9: put <code>[JsonStringEnumMemberName(\"UPI\")]</code> on <code>PaymentMode.Upi</code> so the file says <code>\"UPI\"</code>.</li>
</ul>
''',
iqs=[("Basic","Why does the store save to a temp file and then replace the real file?","Writing directly truncates the file first, so a crash, power cut or full disk mid-write leaves a corrupt or empty file and all data is lost. Writing a complete temp file and then swapping it in with a rename/replace on the same volume means the real file is always either the old version or the new one. File.Replace also keeps a .bak."),
("Basic","Why is IExpenseStore an interface?","The service depends on the abstraction, not on JSON files. You can swap in an in-memory store for tests, or SQLite/EF Core later (Phase 2), without changing ExpenseService or the UI. It's the same idea as Week 4's IRepository&lt;T&gt;."),
("Intermediate","Why does ExpenseService save before updating its in-memory list?","If SaveAsync throws (locked file, disk full, no permission), the in-memory list is left untouched, so what the user sees still matches what's on disk. Updating memory first would show changes that were never persisted."),
("Intermediate","Why store a version number in the JSON file?","The file outlives the code. When the schema changes (e.g. splitting Note into Payee and Note, or adding currency), the loader can detect old files and migrate them, and an old app can refuse a file written by a newer one instead of misreading it.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Monthly reports, budget alerts, CSV export and hardening",
"Finish the expense tracker: monthly LINQ summaries by category and payment mode, month-over-month trend, top 5 expenses, budget alerts from configuration, CSV export, logging polish, then try to break it, document it, push it and revise the week.",
[("Aggregation","Combining many rows into summary values: Sum, Count, Average, grouped by a key."),
("Month-over-month (MoM)","Percentage change from one month's total to the next."),
("Budget threshold","A limit from configuration; an alert fires when spending reaches a set percentage of it."),
("CSV escaping","Wrapping a field in quotes (and doubling inner quotes) when it contains a comma, quote or newline."),
("CSV injection","A cell starting with <code>=</code>, <code>+</code>, <code>-</code> or <code>@</code> that spreadsheet apps may run as a formula.")],
["Reports are pure functions over <code>IEnumerable&lt;Expense&gt;</code>, so they're easy to test.",
"Budgets live in configuration; unknown category names are logged as warnings rather than ignored silently.",
"CSV is written with a UTF-8 BOM so Excel shows ₹ correctly.",
"LoggerMessage methods give the store's events fixed EventIds.",
"Re-run the try-to-break table after every change."],
f'''
<h3>1. Budget options and report models</h3>
{C(r"""
{
  "Storage": { "DataFile": "expenses.json" },
  "Budget": {
    "MonthlyTotal": 40000,
    "WarnAtPercent": 80,
    "Categories": {
      "Food": 8000,
      "Shopping": 5000,
      "Entertainment": 2000
    }
  },
  "Export": { "Folder": "exports" },
  "Logging": {
    "LogLevel": { "Default": "Warning", "ExpenseTracker": "Warning" },
    "Console": { "FormatterName": "simple", "FormatterOptions": { "SingleLine": true, "TimestampFormat": "HH:mm:ss " } }
  }
}
""", "ExpenseTracker.App/appsettings.json (updated)", lang="json")}
{C(r"""
{
  "Logging": { "LogLevel": { "ExpenseTracker": "Debug" } }
}
""", "ExpenseTracker.App/appsettings.Development.json", lang="json")}
{C(r"""
using ExpenseTracker.Core.Models;

namespace ExpenseTracker.Core.Reports;

public sealed class BudgetOptions
{
    public const string SectionName = "Budget";

    public decimal MonthlyTotal { get; set; }                 // 0 = no overall budget
    public decimal WarnAtPercent { get; set; } = 80;
    public Dictionary<string, decimal> Categories { get; set; } = new();
}

public sealed record CategoryTotal(Category Category, decimal Total, int Count, decimal SharePercent);
public sealed record ModeTotal(PaymentMode Mode, decimal Total, int Count);
public sealed record MonthTotal(int Year, int Month, decimal Total, decimal? ChangePercent);

public sealed record BudgetAlert(string Scope, decimal Spent, decimal Limit)
{
    public decimal PercentUsed => Limit == 0 ? 0 : Math.Round(Spent / Limit * 100, 1);
    public bool IsOver => Spent > Limit;
}
""", "ExpenseTracker.Core/Reports/ReportModels.cs")}

<h3>2. ReportService: last week's LINQ, put to work</h3>
{C(r"""
using ExpenseTracker.Core.Models;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace ExpenseTracker.Core.Reports;

public sealed class ReportService
{
    private readonly BudgetOptions _budget;
    private readonly ILogger<ReportService> _logger;
    private readonly Dictionary<Category, decimal> _categoryLimits = new();

    public ReportService(IOptions<BudgetOptions> options, ILogger<ReportService> logger)
    {
        _budget = options.Value;
        _logger = logger;

        // Turn config strings into enum keys once; complain about typos instead of ignoring them
        foreach (var (name, limit) in _budget.Categories)
        {
            if (Enum.TryParse(name, ignoreCase: true, out Category category) && Enum.IsDefined(category))
                _categoryLimits[category] = limit;
            else
                _logger.LogWarning("Budget:Categories has unknown category {Name}; ignoring it", name);
        }
    }

    public static IEnumerable<Expense> InMonth(IEnumerable<Expense> expenses, int year, int month) =>
        expenses.Where(e => e.Date.Year == year && e.Date.Month == month);

    public IReadOnlyList<CategoryTotal> ByCategory(IEnumerable<Expense> expenses, int year, int month)
    {
        var inMonth = InMonth(expenses, year, month).ToList();     // materialise once (Week 4)
        decimal grandTotal = inMonth.Sum(e => e.Amount);

        return inMonth
            .GroupBy(e => e.Category)
            .Select(g =>
            {
                decimal total = g.Sum(e => e.Amount);
                decimal share = grandTotal == 0 ? 0 : Math.Round(total / grandTotal * 100, 1);
                return new CategoryTotal(g.Key, total, g.Count(), share);
            })
            .OrderByDescending(c => c.Total)
            .ToList();
    }

    public IReadOnlyList<ModeTotal> ByPaymentMode(IEnumerable<Expense> expenses, int year, int month) =>
        InMonth(expenses, year, month)
            .GroupBy(e => e.PaymentMode)
            .Select(g => new ModeTotal(g.Key, g.Sum(e => e.Amount), g.Count()))
            .OrderByDescending(m => m.Total)
            .ToList();

    public IReadOnlyList<MonthTotal> MonthOverMonth(IEnumerable<Expense> expenses, int lastMonths = 6)
    {
        var totals = expenses
            .GroupBy(e => (e.Date.Year, e.Date.Month))
            .Select(g => (g.Key.Year, g.Key.Month, Total: g.Sum(e => e.Amount)))
            .OrderBy(t => t.Year).ThenBy(t => t.Month)
            .TakeLast(lastMonths)
            .ToList();

        var result = new List<MonthTotal>();
        decimal? previous = null;
        foreach (var (year, month, total) in totals)
        {
            decimal? change = previous is > 0m
                ? Math.Round((total - previous.Value) / previous.Value * 100, 1)
                : null;
            result.Add(new MonthTotal(year, month, total, change));
            previous = total;
        }
        return result;   // months with no spending simply don't appear
    }

    public static IReadOnlyList<Expense> TopExpenses(IEnumerable<Expense> expenses, int year, int month, int count = 5) =>
        InMonth(expenses, year, month)
            .OrderByDescending(e => e.Amount)
            .ThenBy(e => e.Date)
            .Take(count)
            .ToList();

    public IReadOnlyList<BudgetAlert> BudgetAlerts(IEnumerable<Expense> expenses, int year, int month)
    {
        var inMonth = InMonth(expenses, year, month).ToList();
        var alerts = new List<BudgetAlert>();

        if (_budget.MonthlyTotal > 0)
            Check("Total", inMonth.Sum(e => e.Amount), _budget.MonthlyTotal);

        foreach (var (category, limit) in _categoryLimits)
            Check(category.ToString(), inMonth.Where(e => e.Category == category).Sum(e => e.Amount), limit);

        foreach (var alert in alerts.Where(a => a.IsOver))
            _logger.LogWarning("Budget exceeded for {Scope} in {Year}-{Month:D2}: {Spent} of {Limit}",
                               alert.Scope, year, month, alert.Spent, alert.Limit);

        return alerts.OrderByDescending(a => a.PercentUsed).ToList();

        void Check(string scope, decimal spent, decimal limit)
        {
            if (limit > 0 && spent >= limit * _budget.WarnAtPercent / 100)
                alerts.Add(new BudgetAlert(scope, spent, limit));
        }
    }
}
""", "ExpenseTracker.Core/Reports/ReportService.cs")}

<h3>3. CSV export</h3>
{C(r"""
using System.Globalization;
using System.Text;
using ExpenseTracker.Core.Models;

namespace ExpenseTracker.Core.Reports;

public static class CsvExporter
{
    public static async Task<int> ExportAsync(IEnumerable<Expense> expenses, string path, CancellationToken ct = default)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);

        // BOM on purpose: Excel needs it to read ₹ and Indian-language notes correctly (Monday)
        await using var writer = new StreamWriter(path, append: false, new UTF8Encoding(encoderShouldEmitUTF8Identifier: true));
        await writer.WriteLineAsync("Id,Date,Category,Amount,PaymentMode,Note");

        int rows = 0;
        foreach (var e in expenses.OrderBy(e => e.Date).ThenBy(e => e.Id))
        {
            ct.ThrowIfCancellationRequested();
            string line = string.Join(',',
                e.Id.ToString(CultureInfo.InvariantCulture),
                e.Date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                e.Category.ToString(),
                e.Amount.ToString(CultureInfo.InvariantCulture),   // 1249.75, never "1,249.75"
                e.PaymentMode == PaymentMode.Upi ? "UPI" : e.PaymentMode.ToString(),
                Escape(e.Note));
            await writer.WriteLineAsync(line);
            rows++;
        }
        return rows;
    }

    internal static string Escape(string? value)
    {
        if (string.IsNullOrEmpty(value)) return "";

        // Neutralise spreadsheet formulas: =HYPERLINK(...) in a note must stay text
        if (value[0] is '=' or '+' or '-' or '@') value = "'" + value;

        bool needsQuotes = value.IndexOfAny([',', '"', '\n', '\r']) >= 0;
        return needsQuotes ? '"' + value.Replace("\"", "\"\"") + '"' : value;
    }
}
""", "ExpenseTracker.Core/Reports/CsvExporter.cs")}

<h3>4. Logging polish</h3>
<p>Replace the store's ad-hoc log calls with generated methods that have fixed EventIds, and time each save. Ops tooling can then alert on event 3003 (save failed) without parsing message text.</p>
{C(r"""
using Microsoft.Extensions.Logging;

namespace ExpenseTracker.Core.Storage;

internal static partial class StoreLog
{
    [LoggerMessage(EventId = 3001, Level = LogLevel.Information, Message = "Loaded {Count} expenses from {Path}")]
    public static partial void Loaded(ILogger logger, int count, string path);

    [LoggerMessage(EventId = 3002, Level = LogLevel.Information, Message = "Saved {Count} expenses to {Path} in {ElapsedMs} ms")]
    public static partial void Saved(ILogger logger, int count, string path, long elapsedMs);

    [LoggerMessage(EventId = 3003, Level = LogLevel.Error, Message = "Saving to {Path} failed")]
    public static partial void SaveFailed(ILogger logger, Exception exception, string path);

    [LoggerMessage(EventId = 3004, Level = LogLevel.Error, Message = "Data file {Path} is corrupt near line {Line}")]
    public static partial void Corrupt(ILogger logger, Exception exception, string path, long? line);
}
""", "ExpenseTracker.Core/Storage/StoreLog.cs")}
{C(r"""
// JsonFileExpenseStore.SaveAsync — changes
var stopwatch = System.Diagnostics.Stopwatch.StartNew();
// ... write temp file, replace ...
StoreLog.Saved(_logger, doc.Expenses.Count, Location, stopwatch.ElapsedMilliseconds);

// in the catch block
StoreLog.SaveFailed(_logger, ex, Location);

// LoadAsync — JsonException catch
StoreLog.Corrupt(_logger, ex, Location, ex.LineNumber + 1);
""", "ExpenseTracker.Core/Storage/JsonFileExpenseStore.cs (changes)")}
{C(r"""
// ExpenseService.UpdateAsync / DeleteAsync — add a scope so every line (including the store's) carries the id
using var scope = logger.BeginScope("Expense {ExpenseId}", id);
""", "ExpenseTracker.Core/Services/ExpenseService.cs (changes)")}

<h3>5. Wire the new features into the app</h3>
{C(r"""
// Program.cs — registration (before builder.Build())
builder.Services.Configure<BudgetOptions>(builder.Configuration.GetSection(BudgetOptions.SectionName));
builder.Services.AddSingleton<ReportService>();

// after Build()
var reports = host.Services.GetRequiredService<ReportService>();
string exportFolder = builder.Configuration["Export:Folder"] ?? "exports";

// Menu: add "5) Monthly summary   6) Export CSV", ReadInt("Choose: ", 0, 6), and:
//   case 5: PrintMonthlySummary(); break;
//   case 6: await ExportCsvAsync(); break;
// Add `using ExpenseTracker.Core.Reports;` at the top.

void PrintMonthlySummary()
{
    DateOnly any = ConsoleInput.ReadDate("Any date in the month (Enter = this month): ", DateOnly.FromDateTime(DateTime.Today));
    var all = expenses.All;
    Console.WriteLine($"\n  ── {any:MMMM yyyy} ──");

    Console.WriteLine("  By category");
    foreach (var c in reports.ByCategory(all, any.Year, any.Month))
        Console.WriteLine($"    {c.Category,-13} {Display.Rupees(c.Total),14} {c.SharePercent,6:0.0}%  ({c.Count})");

    Console.WriteLine("  By payment mode");
    foreach (var m in reports.ByPaymentMode(all, any.Year, any.Month))
        Console.WriteLine($"    {Display.Mode(m.Mode),-13} {Display.Rupees(m.Total),14}  ({m.Count})");

    Console.WriteLine("  Top 5");
    foreach (var e in ReportService.TopExpenses(all, any.Year, any.Month))
        Console.WriteLine($"    {e.Date:dd MMM}  {Display.Rupees(e.Amount),14}  {e.Category}  {e.Note}");

    Console.WriteLine("  Month over month");
    foreach (var t in reports.MonthOverMonth(all))
    {
        string change = t.ChangePercent is { } p ? $"{p,6:+0.0;-0.0;0.0}%" : "      –";
        Console.WriteLine($"    {new DateOnly(t.Year, t.Month, 1):MMM yyyy}  {Display.Rupees(t.Total),14}  {change}");
    }

    var alerts = reports.BudgetAlerts(all, any.Year, any.Month);
    if (alerts.Count > 0) Console.WriteLine("  Budget");
    foreach (var a in alerts)
    {
        Console.ForegroundColor = a.IsOver ? ConsoleColor.Red : ConsoleColor.Yellow;
        Console.WriteLine($"    {(a.IsOver ? "✗ Over" : "⚠ Near"),-7} {a.Scope,-13} {Display.Rupees(a.Spent)} of {Display.Rupees(a.Limit)} ({a.PercentUsed}%)");
        Console.ResetColor();
    }
}

async Task ExportCsvAsync()
{
    string fileName = $"expenses-{DateTime.Now:yyyyMMdd-HHmmss}.csv";
    string folder = Path.IsPathRooted(exportFolder)
        ? exportFolder
        : Path.Combine(Path.GetDirectoryName(store.Location)!, exportFolder);
    string path = Path.Combine(folder, fileName);

    int rows = await CsvExporter.ExportAsync(expenses.All, path);
    Console.WriteLine($"  ✓ Exported {rows} rows to {path}");
}
""", "ExpenseTracker.App/Program.cs (additions)")}
{C(r"""
Choose: 5
Any date in the month (Enter = this month):
  ── November 2026 ──
  By category
    Rent              ₹18,500.00   55.8%  (1)
    Food               ₹7,120.00   21.5%  (14)
    Groceries          ₹4,310.25   13.0%  (3)
    Shopping           ₹3,210.00    9.7%  (2)
  By payment mode
    UPI               ₹29,880.25  (16)
    Card               ₹2,999.00  (1)
    Cash                 ₹261.00  (3)
  Top 5
    05 Nov      ₹18,500.00  Rent  November rent
    14 Nov       ₹2,999.00  Shopping  Diwali kurta
    21 Nov       ₹1,560.50  Groceries  DMart monthly stock
    ...
  Month over month
    Sep 2026      ₹31,450.00        –
    Oct 2026      ₹42,180.00   +34.1%
    Nov 2026      ₹33,140.25   -21.4%
  Budget
    ⚠ Near  Food          ₹7,120.00 of ₹8,000.00 (89.0%)
    ⚠ Near  Total         ₹33,140.25 of ₹40,000.00 (82.9%)
""", "Sample output", lang="text")}

<h3>6. Try to break it</h3>
{table(["Scenario","Expected"],[
["Delete <code>expenses.json</code>, run, add one expense","\"No data file… starting empty\"; folder and file created on first save"],
["Remove a closing <code>]</code> from the JSON by hand, then start","Refuses to start: \"corrupt near line N… restore .bak\", exit code 1, file untouched"],
["Replace the whole file content with <code>null</code>","Refuses to start: \"contains 'null' instead of expense data\""],
["Change a category to <code>\"Travel\"</code> (not in the enum)","JsonException → corrupt-file message pointing at that line"],
["Delete the <code>amount</code> property from one expense","Loads (amount = 0), logs Warning \"1 stored expenses failed validation (ids: 4)\""],
["Set <code>\"version\": 2</code>","Refuses: \"written by a newer version (v2)\""],
["Windows: lock the file from PowerShell <code>$f=[IO.File]::Open($p,'Open','ReadWrite','None')</code>, then add an expense","\"Not saved: …being used by another process\"; list unchanged; no .tmp left behind"],
["Linux/macOS: same test from another tool","Usually succeeds: Unix locks are advisory, so a non-.NET process holding the file doesn't block the rename"],
["Make the data folder read-only (<code>chmod -w</code>) and add","UnauthorizedAccessException → \"Not saved\"; in-memory list unchanged"],
["Amount <code>abc</code>, <code>-50</code>, <code>0</code>, <code>₹1,200</code>","First three re-prompt; ₹1,200 is accepted as 1200"],
["Amount 25,00,000","\"Amount must be between ₹0.01 and ₹10,00,000\" (the limit is formatted with the OS culture, so en-US shows ₹1,000,000)"],
["Edit or delete id 999","\"No expense with id 999\""],
["Note <code>Dinner, \"Barbeque Nation\"</code> then export","CSV cell is <code>\"Dinner, \"\"Barbeque Nation\"\"\"</code>; Excel shows it intact"],
["Note <code>=HYPERLINK(\"http://evil\")</code> then export","Written as <code>'=HYPERLINK…</code>, so Excel shows text and doesn't run a formula"],
["<code>Budget:Categories</code> contains <code>\"Fuel\"</code>","Warning \"unknown category Fuel; ignoring it\""],
["<code>Storage__DataFile=/tmp/x.json</code> environment variable","Uses /tmp/x.json (printed at startup)"],
["Kill the app (Ctrl+C) during a save","Original file intact; at worst a stale <code>.tmp</code>, which the next save overwrites (FileMode.Create)"]])}

<h3>7. README and push</h3>
{C(r"""
# Expense Tracker

Micro-project 4 of my .NET full-stack roadmap (Week 6: files, JSON, logging, configuration).

## Features
- Add, list, edit and delete expenses (₹, UPI / Card / Cash, 10 categories)
- JSON storage with atomic save (temp file + replace) and automatic `.bak`
- Refuses to start on a corrupt data file instead of overwriting it
- Monthly summary: by category, by payment mode, top 5, month-over-month
- Budget alerts from `appsettings.json`
- CSV export (Excel-friendly UTF-8, formula-safe)
- Structured logging with `ILogger` and `[LoggerMessage]`

## Tech
.NET 8 · System.Text.Json · Microsoft.Extensions.Hosting / Configuration / Logging / Options

## Run
```bash
dotnet run --project ExpenseTracker.App
# use another data file
dotnet run --project ExpenseTracker.App -- --Storage:DataFile=/path/to/expenses.json
```

## Configuration
| Key | Default | Meaning |
|-----|---------|---------|
| `Storage:DataFile` | `expenses.json` | Relative paths go under LocalApplicationData/ExpenseTracker |
| `Budget:MonthlyTotal` | `40000` | Overall monthly budget in ₹ (0 = none) |
| `Budget:WarnAtPercent` | `80` | Alert threshold |
| `Budget:Categories:<Name>` | – | Per-category limits |
""", "README.md", lang="markdown")}
{C(r"""
git init
git add .
git commit -m "Expense tracker: JSON store with atomic save, reports, budgets, CSV export"
git branch -M main
git remote add origin https://github.com/<you>/expense-tracker.git
git push -u origin main
""", lang="bash")}
<p>Your real expense data lives in your user profile, not the repo, so there's no risk of committing it. If you ever point <code>Storage:DataFile</code> inside the project, add that path to <code>.gitignore</code>.</p>

<h3>8. Week 6 revision checklist</h3>
<ul>
<li>Path.Combine vs Path.Join; current directory vs AppContext.BaseDirectory vs LocalApplicationData</li>
<li>File one-liners vs FileInfo vs FileStream; FileMode / FileAccess / FileShare</li>
<li>File.ReadLines (lazy) vs ReadAllLines; buffering and Flush; async file APIs and ReadLinesAsync</li>
<li>UTF-8 with and without BOM; why ₹ is 3 bytes; when Excel needs the BOM</li>
<li>JsonSerializer defaults; options (camelCase, indented, enums, ignore nulls, encoder); reuse options</li>
<li>[JsonPropertyName], [JsonIgnore], [JsonRequired], required members; records via constructors</li>
<li>[JsonPolymorphic]/[JsonDerivedType]; JsonDocument vs JsonNode; source generation, what and why</li>
<li>IDisposable, using statement vs declaration, disposal order, full Dispose pattern, SafeHandle, IAsyncDisposable</li>
<li>ILogger levels, categories, message templates, exceptions, scopes, filters, LoggerMessage</li>
<li>Configuration providers and precedence, <code>__</code> in env vars, binding, validation, user secrets, Generic Host, IOptions variants</li>
<li>Atomic save with temp file + replace; save-then-commit in memory; refuse to start on corrupt data</li>
</ul>

<h3>9. Quick quiz: predict the output</h3>
<details><summary>Q1. On Linux, what prints?</summary>
{C(r"""
Console.WriteLine(Path.Combine("data", "/etc/hosts"));
Console.WriteLine(Path.Join("data", "/etc/hosts"));
""")}<b>/etc/hosts</b> then <b>data/etc/hosts</b>. Combine restarts at the rooted second argument. Join simply joins the parts and doesn't add a separator because the second part already starts with one.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
var o = new { Name = "Asha", City = (string?)null, Amount = 499m };
Console.WriteLine(JsonSerializer.Serialize(o));
""")}<b>{{"Name":"Asha","City":null,"Amount":499}}</b>. Default options keep PascalCase names, write nulls and produce compact output.</details>
<details><summary>Q3. What prints?</summary>
{C(r"""
var p = JsonSerializer.Deserialize<Person>("{\"name\":\"Ravi\"}")!;
Console.WriteLine(p.Name ?? "(null)");

public class Person { public string? Name { get; set; } }
""")}<b>(null)</b>. Matching is case-sensitive by default, so <code>name</code> doesn't bind to <code>Name</code>, and unknown properties are silently ignored. Use camelCase/case-insensitive options or <code>JsonSerializerDefaults.Web</code>.</details>
<details><summary>Q4. What prints?</summary>
{C(r"""
using var a = new Noisy("A");
using var b = new Noisy("B");
Console.Write("body ");

sealed class Noisy(string n) : IDisposable
{
    public void Dispose() => Console.Write($"{n} ");
}
""")}<b>body B A</b>. Using declarations are disposed at the end of the scope, in reverse order of declaration.</details>
<details><summary>Q5. Does this compile?</summary>
{C(r"""
using var sb = new System.Text.StringBuilder();
sb.Append("₹499");
Console.WriteLine(sb);
""")}<b>No.</b> CS1674: StringBuilder doesn't implement IDisposable, so it can't be used in a using statement or declaration. It holds no OS resources, and the GC handles it.</details>

<div class="note tip"><b>Next week:</b> Week 7, async and concurrency: how async/await really works (state machines, SynchronizationContext, ConfigureAwait), Task vs ValueTask, cancellation with CancellationToken, Task.WhenAll/WhenAny, the thread pool, race conditions, <code>lock</code> and <code>SemaphoreSlim</code>, concurrent collections and Channels. You'll make the expense store safe when several operations save at once.</div>
''',
iqs=[("Basic","How does your app behave if the JSON data file is corrupt, and why?","It refuses to start: the JsonException is caught, logged with the line number, wrapped in ExpenseStoreException, and the app exits with code 1 without touching the file. Starting empty would let the next save overwrite the user's real data. The .bak from the last good save gives a recovery path."),
("Basic","Why are budget limits in configuration rather than code?","They're user or environment decisions, not logic. Config lets them change without recompiling, lets each environment differ, and lets them be overridden by environment variables or the command line. Validating them at startup (unknown categories logged) keeps typos from being silently ignored."),
("Intermediate","What are the pitfalls of writing CSV by hand, and how did you handle them?","Fields containing commas, quotes or newlines must be quoted with inner quotes doubled. Numbers and dates must use an invariant format, not the current culture (1,249.75 vs 1249,75). Excel needs a UTF-8 BOM for non-ASCII. Cells starting with = + - @ can execute as formulas (CSV injection), so they're prefixed with an apostrophe. For anything bigger, use a library like CsvHelper."),
("Intermediate","How would you move this app from a JSON file to SQLite or SQL Server?","Write a new IExpenseStore (or a repository) backed by EF Core and register it in DI instead of JsonFileExpenseStore. ExpenseService, reports and the UI don't change. With a database you'd also switch from save-the-whole-list to per-row insert/update/delete inside transactions, and let unique keys and constraints enforce what Validate() checks today.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","System.IO: files, paths, streams and encodings","Files &amp; streams","Path.Combine vs Join, File vs FileInfo vs FileStream, ReadLines, async I/O, BOMs and ₹.","2 hrs"),
 (2,"TUE","System.Text.Json","System.Text.Json","Options, attributes, records, required, polymorphism, JsonDocument/JsonNode, source gen.","2 hrs"),
 (3,"WED","IDisposable and the Dispose pattern","IDisposable","using forms, disposal order, full pattern, SafeHandle, IAsyncDisposable, leaks.","2 hrs"),
 (4,"THU","Logging with ILogger","Logging","LoggerFactory, levels, message templates, scopes, filters, LoggerMessage.","2 hrs"),
 (5,"FRI","Configuration and the Generic Host","Configuration","appsettings layers, env vars, command line, options binding, user secrets, Host.","2 hrs"),
 (6,"SAT","Micro-project 4: Expense tracker","Project: expenses","Expense record, IExpenseStore, atomic JSON save, add/list/edit/delete, config, ILogger.","4 hrs"),
 (7,"SUN","Reports, budgets, CSV and hardening","Reports &amp; revision","Monthly LINQ summaries, budget alerts, CSV export, try-to-break, README, quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week06.html", 6,
      "Week 6 — File I/O and serialization", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 6 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Micro-project 4"],
      "Until now every program forgot everything when it closed. This week your apps start remembering: you'll read and write files safely across operating systems, turn objects into JSON and back, release resources deterministically, and replace Console.WriteLine debugging with real logging and configuration, using the same building blocks ASP.NET Core uses. You'll finish with an expense tracker that stores ₹ amounts in JSON, saves atomically and reports monthly budgets.",
      cards, days)
print("built")
