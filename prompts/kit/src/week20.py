import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Authentication, Authorisation and JWT Fundamentals",
"Understand the difference between AuthN and AuthZ, compare cookie vs token strategies, dissect a JWT, and reason clearly about where tokens should be stored and why HTTPS is non-negotiable.",
[("Authentication (AuthN)","Proving who you are — verifying identity, e.g. entering a password or OTP."),
("Authorisation (AuthZ)","Deciding what you are allowed to do once identity is established."),
("Cookie-based session","Server stores session data, sends a session ID in a Set-Cookie header; browser resends it automatically."),
("Token-based (JWT)","Server issues a signed token; client stores it and sends it in the Authorization header."),
("JWT (JSON Web Token)","A compact, URL-safe token with three Base64Url parts: header.payload.signature."),
("Header","First JWT part: algorithm (<code>alg</code>) and type (<code>typ</code>)."),
("Payload","Second JWT part: claims — standard (<code>sub</code>, <code>exp</code>, <code>iat</code>, <code>iss</code>, <code>aud</code>) plus custom."),
("Signature","Third JWT part: HMAC or RSA over header + payload using the secret or private key."),
("Claim","A statement about a subject, e.g. <code>role: admin</code> or <code>mobile: +919876543210</code>."),
("HMAC-SHA256 (HS256)","Symmetric signing — same secret signs and verifies. Good for a single service."),
("RS256","Asymmetric RSA signing — private key signs, public key verifies. Services can verify without the secret."),
("XSS (Cross-Site Scripting)","Injected script reads <code>localStorage</code>; a reason NOT to store tokens there."),
("CSRF (Cross-Site Request Forgery)","Tricks the browser into sending a cookie to your server from another site."),
("HTTPS","TLS over HTTP; encrypts the channel so tokens can't be intercepted in transit.")],
["AuthN always comes before AuthZ — you must know who someone is before deciding what they can do.",
"JWTs are <b>signed, not encrypted</b>. Anyone can Base64-decode the payload. Never put secrets (Aadhaar number, CVV) in a JWT.",
"<b>HMAC:</b> single shared secret — fast, fine for a monolith. <b>RSA:</b> private key signs, public key verifies — needed when other services or mobile clients verify tokens without the secret.",
"<code>exp</code> (expiry) is a Unix timestamp in seconds, not milliseconds.",
"<b>localStorage</b> is XSS-vulnerable — an injected script can steal the token. <b>HttpOnly cookies</b> are immune to XSS but need CSRF protection. Many SPAs choose cookies for access tokens in production.",
"HTTPS is not optional. Without it, every token you issue travels in plaintext across the network."],
f'''
<h3>1. AuthN vs AuthZ — why the distinction matters</h3>
<p>When a customer of <em>Ugaav Agro</em>'s ordering portal logs in, two checks happen in sequence:</p>
{table(["Step","Question answered","Example decision"],[
["Authentication","Is this really Priya Sharma?","OTP to +91 98765 43210 matches → identity confirmed"],
["Authorisation","Can Priya access this route?","Role = <code>farmer</code> → can place orders, cannot view admin dashboard"]])}
<p>A bug that swaps these is catastrophic: authorisation without authentication lets anyone reach admin pages.</p>

<h3>2. Cookies vs Tokens</h3>
{table(["","Cookie/Session","JWT (token)"],[
["Where state lives","Server (session store)","Client (token is self-contained)"],
["Scalability","Need sticky sessions or shared cache","Stateless — any server can verify"],
["Revocation","Delete session from store → instant","Tricky — token stays valid until expiry (see Thu: refresh tokens)"],
["XSS exposure","HttpOnly cookie not reachable from JS","localStorage / JS-accessible cookie is reachable"],
["CSRF risk","Yes, if cookie sent automatically","No, unless stored in a cookie"],
["Best for","Traditional server-rendered apps","SPAs, mobile apps, microservices"]])}

<h3>3. JWT anatomy</h3>
<p>A JWT is three Base64Url-encoded JSON objects joined by dots: <code>header.payload.signature</code>.</p>
{C(r"""
// --- Decoded header ---
{
  "alg": "HS256",    // HMAC-SHA256
  "typ": "JWT"
}

// --- Decoded payload (claims) ---
{
  "sub": "user_42",                     // subject (user ID)
  "name": "Priya Sharma",
  "mobile": "+919876543210",
  "role": "farmer",
  "iss": "ugaav-auth",                  // issuer
  "aud": "ugaav-orders",               // audience
  "iat": 1700000000,                    // issued-at (Unix seconds)
  "exp": 1700003600                     // expires-at (Unix seconds) — 1 hour later
}

// --- Signature ---
// HMAC_SHA256(
//   base64url(header) + "." + base64url(payload),
//   SECRET_KEY                        // server holds this; never send it to clients
// )
""", "jwt-anatomy.json", lang="json")}
{warn("The payload is Base64Url-encoded, NOT encrypted. Paste any JWT into jwt.io and you can read every claim. Never put a user's password, Aadhaar number, CVV, or any private data in a JWT claim.")}

<h3>4. HMAC vs RSA signing</h3>
{C(r"""
// HMAC-SHA256 (HS256) — symmetric
// One secret: sign with it, verify with it
// If a second service needs to verify tokens, it must also have the secret → risk of exposure

// RS256 — asymmetric RSA
// Private key (server keeps safe): signs tokens
// Public key (can be published as JWKS endpoint): verifies tokens
// A mobile app or microservice downloads the public key and verifies locally — never touches the secret

// Choosing:
// Single API + single trust boundary  → HS256 is fine, simpler
// Multiple services or public clients → RS256 (or ES256 — ECDSA, same idea, smaller keys)
""", lang="text")}
{table(["","HS256","RS256"],[
["Key type","Single shared secret","Private key (signs) + public key (verifies)"],
["Speed","Faster","Slower (RSA math)"],
["Secret exposure","Every verifier needs the secret","Verifiers only need the public key"],
["Key rotation","Must redistribute secret to all verifiers","Rotate private key, publish new public key"],
["Use case","Single API, internal services","Microservices, public JWKS, mobile clients"]])}

<h3>5. Token storage risks</h3>
{C(r"""
// OPTION 1: localStorage / sessionStorage
// ✗ Readable by any JavaScript on the page
// ✗ XSS attack steals token with document.cookie is not needed; localStorage.getItem("token") works
// ✓ No automatic CSRF risk

// OPTION 2: HttpOnly Secure cookie
// ✓ Not readable by JavaScript at all (XSS can't steal it)
// ✓ Sent only over HTTPS (Secure flag)
// ✗ Browser sends it automatically → CSRF risk (mitigate with SameSite=Strict/Lax + CSRF token)

// OPTION 3: In-memory (JS variable)
// ✓ XSS can't survive a page reload (token is gone)
// ✗ Lost on refresh → needs silent re-auth (refresh token in HttpOnly cookie)
""", lang="text")}

<h3>6. Why HTTPS is non-negotiable</h3>
<p>Without TLS, an attacker on the same Wi-Fi (café, airport) can read your Authorization header
and replay the JWT for the token's full lifetime. All traffic between the mobile app and
Ugaav's API must be over HTTPS. Use <code>app.UseHttpsRedirection()</code> in development;
ensure your hosting (Azure App Service, AWS ALB) terminates TLS in production.</p>
{C(r"""
// Program.cs — always present in production
app.UseHttpsRedirection();

// In development (launchSettings.json sets HTTPS port automatically)
// dotnet dev-certs https --trust    ← run once per machine
""", "Program.cs (excerpt)")}
''',
["Saying 'JWT is encrypted' — it is signed. Tampered payloads are rejected, but anyone can read them.",
"Putting sensitive data (passwords, PAN numbers) in a JWT claim.",
"Using HS256 when multiple independent services verify tokens — they'd all need the secret.",
"Storing JWTs in localStorage in a production SPA facing real XSS risk.",
"Forgetting to set an expiry (<code>exp</code>) claim — the token is then valid forever.",
"Confusing authentication (who) with authorisation (can they?)."],
("35 min", ["Paste any JWT from jwt.io's playground into a base64 decoder manually — confirm you can read the payload without the secret.",
"Draw on paper: HTTP request flow for cookie-session auth vs JWT auth. Label where AuthN and AuthZ happen.",
"List three claim types you would and three you would NOT put in a JWT for a fintech app. Justify each."]),
[("What does JWT stand for and what are its three parts?","JSON Web Token. Header (algorithm + type), Payload (claims), Signature (HMAC or RSA over header+payload)."),
("Signed vs encrypted — what does 'signed' mean for a JWT?","The signature lets any holder of the key verify that the token hasn't been tampered with. The payload is still readable by anyone; it is not encrypted."),
("When would you prefer RS256 over HS256?","When multiple independent services or public clients need to verify tokens. They receive the public key and verify locally without ever receiving the secret private key.")],
[("Basic","What is the difference between authentication and authorisation?","Authentication proves identity — are you who you claim to be? Authorisation decides what an authenticated identity may do. AuthN comes first; without it, AuthZ has no subject to evaluate."),
("Basic","Why are JWTs called 'self-contained'?","All the information needed to authorise a request (user ID, roles, expiry) is encoded in the token itself. The server doesn't need a database round-trip to validate — it just verifies the signature and reads the claims."),
("Basic","Name two risks of storing a JWT in localStorage.","(1) XSS — injected JavaScript can call localStorage.getItem and exfiltrate the token. (2) Persistent across tabs/sessions; a stolen token stays usable until expiry."),
("Intermediate","What is CSRF and how does it relate to cookie-based auth?","CSRF tricks the browser into making an authenticated request to your server from a malicious page, because the browser automatically attaches cookies. Mitigations: SameSite cookie attribute (Strict or Lax), CSRF tokens in forms, or not using cookies and requiring an explicit Authorization header."),
("Intermediate","Your company has an ASP.NET Core API, an iOS app, and a React SPA — all using the same auth service. Should you use HS256 or RS256? Why?","RS256. The iOS app and React SPA can verify tokens using the published public key (JWKS endpoint) without ever receiving the secret. With HS256 you'd need to give the secret to every verifier, increasing the blast radius if it leaks."),
("Advanced","A JWT's exp claim has passed but the user is still active. What are your options for keeping them logged in without asking them to re-enter their password?","Issue a short-lived access token (15 min) paired with a long-lived refresh token stored securely (HttpOnly cookie or secure storage). When the access token expires, the client exchanges the refresh token for a new access token silently. Rotate the refresh token on each use to detect reuse attacks. This is Thursday's topic.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "ASP.NET Core Identity",
"Wire up ASP.NET Core Identity to your API — IdentityDbContext, ApplicationUser, password options, UserManager, SignInManager, RoleManager, and seeding roles and an admin account.",
[("ASP.NET Core Identity","A membership system providing user storage, password hashing, roles, claims, lockout, and two-factor support — integrated with EF Core."),
("IdentityDbContext","An EF Core DbContext that includes all Identity tables (AspNetUsers, AspNetRoles, AspNetUserRoles, AspNetUserClaims, etc.)."),
("ApplicationUser","Your custom user class inheriting from <code>IdentityUser</code>; add extra columns here (e.g. FullName, MobileNumber)."),
("IdentityUser","The base Identity user with Id (Guid string), UserName, Email, PasswordHash, PhoneNumber, LockoutEnabled, etc."),
("UserManager&lt;T&gt;","Service for user CRUD: CreateAsync, FindByEmailAsync, CheckPasswordAsync, AddToRoleAsync, GetClaimsAsync."),
("SignInManager&lt;T&gt;","Service for sign-in flows: PasswordSignInAsync, SignOutAsync — also handles lockout and 2FA."),
("RoleManager&lt;T&gt;","Service for creating and querying roles: CreateAsync, RoleExistsAsync."),
("PasswordHasher","Hashes passwords with PBKDF2+SHA512 by default; never store plain-text passwords."),
("LockoutOptions","How many failed attempts trigger a lockout and for how long."),
("IdentityResult","Returned by most UserManager operations; has Succeeded, Errors."),
("Data protection","ASP.NET Core's key-ring for protecting tokens (email confirmation, password reset links)."),
("NuGet packages","<code>Microsoft.AspNetCore.Identity.EntityFrameworkCore</code> and an EF Core provider like <code>Microsoft.EntityFrameworkCore.SqlServer</code>.")],
["Identity is a library, not a middleware — you call it via UserManager/SignInManager, not via HTTP pipeline.",
"<code>IdentityUser.Id</code> is a <code>string</code> (GUID by default). If you need an <code>int</code> key, use <code>IdentityUser&lt;int&gt;</code>.",
"Never call <code>SaveChangesAsync</code> after <code>UserManager.CreateAsync</code> — Identity does it for you.",
"<code>PasswordSignInAsync</code> returns a <code>SignInResult</code>; check <code>.Succeeded</code>, <code>.IsLockedOut</code>, <code>.RequiresTwoFactor</code>.",
"Seeding roles and the admin account should run on startup — not in a migration — so it works in every environment.",
"Identity ships with PBKDF2 (100,000 rounds in .NET 8). Do NOT replace it with MD5 or SHA1."],
f'''
<h3>1. Package references</h3>
{C(r"""
<!-- AuthService.csproj -->
<PackageReference Include="Microsoft.AspNetCore.Identity.EntityFrameworkCore" Version="8.0.0" />
<PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
<PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="8.0.0" PrivateAssets="All" />
<PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.0" />
""", "AuthService.csproj (relevant)", lang="xml")}

<h3>2. ApplicationUser and IdentityDbContext</h3>
{C(r"""
// Models/ApplicationUser.cs
using Microsoft.AspNetCore.Identity;

namespace AuthService.Models;

public class ApplicationUser : IdentityUser
{
    // IdentityUser already has: Id, UserName, Email, PasswordHash,
    //   PhoneNumber, LockoutEnabled, AccessFailedCount, etc.

    // Add your columns here
    public string FullName { get; set; } = string.Empty;

    // Indian context: mobile number is the primary identity for OTP
    // PhoneNumber is already on IdentityUser — just validate the format
}
""", "Models/ApplicationUser.cs")}
{C(r"""
// Data/AppDbContext.cs
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using AuthService.Models;

namespace AuthService.Data;

public class AppDbContext : IdentityDbContext<ApplicationUser>
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    // Add your own DbSets below; Identity tables are added by IdentityDbContext
    public DbSet<RefreshToken> RefreshTokens { get; set; }

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);  // ← MUST call base; Identity tables are configured here

        builder.Entity<RefreshToken>(e =>
        {
            e.HasIndex(r => r.Token).IsUnique();
            e.HasIndex(r => r.UserId);
        });
    }
}
""", "Data/AppDbContext.cs")}

<h3>3. Identity registration in Program.cs</h3>
{C(r"""
// Program.cs
using AuthService.Data;
using AuthService.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// 1. EF Core
builder.Services.AddDbContext<AppDbContext>(opt =>
    opt.UseSqlServer(builder.Configuration.GetConnectionString("Default")));

// 2. Identity
builder.Services.AddIdentity<ApplicationUser, IdentityRole>(opt =>
{
    // Password policy
    opt.Password.RequiredLength = 8;
    opt.Password.RequireDigit = true;
    opt.Password.RequireUppercase = true;
    opt.Password.RequireNonAlphanumeric = false;  // relax for demos

    // Lockout: 5 failed attempts → locked for 10 minutes
    opt.Lockout.MaxFailedAccessAttempts = 5;
    opt.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(10);
    opt.Lockout.AllowedForNewUsers = true;

    // User options
    opt.User.RequireUniqueEmail = true;
})
.AddEntityFrameworkStores<AppDbContext>()   // hooks Identity to your DbContext
.AddDefaultTokenProviders();                // needed for password-reset tokens

// 3. JWT auth — Day 3
// builder.Services.AddAuthentication(...)...
""", "Program.cs (excerpt)")}

<h3>4. UserManager, SignInManager, RoleManager at a glance</h3>
{C(r"""
// All three are injected via constructor DI

public class AuthController(
    UserManager<ApplicationUser> userManager,
    SignInManager<ApplicationUser> signInManager,
    RoleManager<IdentityRole> roleManager) : ControllerBase
{
    // --- Create a user ---
    var user = new ApplicationUser { UserName = "priya.sharma", Email = dto.Email, FullName = dto.FullName };
    IdentityResult result = await userManager.CreateAsync(user, dto.Password);
    if (!result.Succeeded)
        return BadRequest(result.Errors);  // e.g. "Passwords must have at least 8 characters."

    // --- Add to role ---
    await userManager.AddToRoleAsync(user, "Farmer");

    // --- Check password (login) ---
    var found = await userManager.FindByEmailAsync(dto.Email);
    if (found is null) return Unauthorized();
    var signIn = await signInManager.CheckPasswordSignInAsync(found, dto.Password, lockoutOnFailure: true);
    // signIn.Succeeded / .IsLockedOut / .RequiresTwoFactor

    // --- Get user's roles and claims ---
    IList<string> roles  = await userManager.GetRolesAsync(found);
    IList<Claim>  claims = await userManager.GetClaimsAsync(found);
}
""", "Controllers/AuthController.cs (excerpt)")}

<h3>5. Seeding roles and an admin account</h3>
<p>Seed on startup, not in a migration — migrations run on the developer's machine, not production.</p>
{C(r"""
// Data/DbSeeder.cs
using AuthService.Models;
using Microsoft.AspNetCore.Identity;

namespace AuthService.Data;

public static class DbSeeder
{
    public static async Task SeedAsync(IServiceProvider sp)
    {
        var roleManager = sp.GetRequiredService<RoleManager<IdentityRole>>();
        var userManager = sp.GetRequiredService<UserManager<ApplicationUser>>();
        var cfg         = sp.GetRequiredService<IConfiguration>();

        string[] roles = ["Admin", "Farmer", "Buyer"];
        foreach (var role in roles)
            if (!await roleManager.RoleExistsAsync(role))
                await roleManager.CreateAsync(new IdentityRole(role));

        // Seed admin — credentials come from user-secrets or environment variables
        string adminEmail = cfg["Seed:AdminEmail"] ?? "admin@ugaav.in";
        string adminPass  = cfg["Seed:AdminPassword"]
            ?? throw new InvalidOperationException("Seed:AdminPassword not configured");

        if (await userManager.FindByEmailAsync(adminEmail) is null)
        {
            var admin = new ApplicationUser
            {
                UserName = adminEmail,
                Email    = adminEmail,
                FullName = "Super Admin",
                EmailConfirmed = true
            };
            var result = await userManager.CreateAsync(admin, adminPass);
            if (result.Succeeded)
                await userManager.AddToRoleAsync(admin, "Admin");
        }
    }
}
""", "Data/DbSeeder.cs")}
{C(r"""
// Program.cs — call seeder after building the app
var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.MigrateAsync();             // apply pending migrations
    await DbSeeder.SeedAsync(scope.ServiceProvider);
}
""", "Program.cs (startup)")}

<h3>6. Identity tables created by EF Core</h3>
{table(["Table","Purpose"],[
["<code>AspNetUsers</code>","One row per user; Id, PasswordHash, Email, LockoutEnd, AccessFailedCount…"],
["<code>AspNetRoles</code>","Role names (Admin, Farmer, Buyer)"],
["<code>AspNetUserRoles</code>","Many-to-many join: which user is in which role"],
["<code>AspNetUserClaims</code>","Per-user extra claims stored in the DB"],
["<code>AspNetUserLogins</code>","External login providers (Google, Microsoft)"],
["<code>AspNetUserTokens</code>","Tokens for password reset, email confirmation"],
["<code>AspNetRoleClaims</code>","Claims attached to a role"]])}
''',
["Calling <code>context.SaveChangesAsync()</code> after <code>userManager.CreateAsync()</code> — double write, may cause duplicate-key errors.",
"Not calling <code>base.OnModelCreating(builder)</code> in <code>IdentityDbContext</code> — Identity tables won't be configured.",
"Storing the admin seed password hard-coded in source code — use user-secrets or environment variables.",
"Forgetting <code>.AddDefaultTokenProviders()</code> — password reset emails throw at runtime.",
"Using <code>AddAuthentication().AddIdentityCookies()</code> instead of <code>AddIdentity()</code> and then wondering why JWT auth doesn't work."],
("40 min", ["Scaffold the AuthService project with <code>dotnet new webapi -n AuthService</code>, add the NuGet packages, and create <code>ApplicationUser</code> + <code>AppDbContext</code>.",
"Run <code>dotnet ef migrations add InitialIdentity</code> and inspect the generated migration — verify the AspNetUsers and AspNetRoles tables are present.",
"Implement the <code>DbSeeder</code> and confirm the admin user and three roles are created on startup."]),
[("What is IdentityDbContext?","An EF Core DbContext preconfigured with all the Identity tables (AspNetUsers, AspNetRoles, AspNetUserRoles, etc.). You inherit from it and add your own DbSets."),
("Why not call SaveChangesAsync after CreateAsync?","UserManager.CreateAsync already calls SaveChangesAsync internally. Calling it again risks a second write or concurrency conflicts."),
("What does LockoutOnFailure: true do in CheckPasswordSignInAsync?","It increments AccessFailedCount on each failure. When it reaches MaxFailedAccessAttempts, Identity sets LockoutEnd to now + LockoutTimeSpan and all sign-in attempts return IsLockedOut until the period expires.")],
[("Basic","What tables does ASP.NET Core Identity create?","AspNetUsers (users), AspNetRoles (roles), AspNetUserRoles (many-to-many), AspNetUserClaims, AspNetUserLogins (OAuth), AspNetUserTokens, and AspNetRoleClaims. All are configured by AddIdentity and IdentityDbContext."),
("Basic","What is the difference between UserManager and SignInManager?","UserManager handles CRUD on users: create, find, update, password check, role and claim management. SignInManager manages sign-in flows including lockout, 2FA, and external providers. For a JWT API you often use only UserManager and build tokens yourself."),
("Basic","How does Identity store passwords?","It uses PBKDF2 with SHA-512, 100,000 iterations by default in .NET 8. The hash, salt, and iteration count are all stored in the PasswordHash column; plain text is never stored."),
("Intermediate","How do you add a custom field (e.g. MobileNumber) to the Identity user?","Inherit from IdentityUser to create ApplicationUser, add the property, use ApplicationUser throughout. The EF Core migration will add the column to AspNetUsers."),
("Intermediate","Why seed roles in code rather than a migration?","Migrations run once and are specific to the developer's DB; they don't re-run. Startup seeding runs on every deploy, ensuring every environment (dev, staging, prod) has the required roles, and idempotent checks (RoleExistsAsync) prevent duplicates."),
("Intermediate","How does lockout work in ASP.NET Core Identity?","Every failed CheckPasswordSignInAsync with lockoutOnFailure:true increments AccessFailedCount. When it hits MaxFailedAccessAttempts, LockoutEnd is set. Until that time all logins return IsLockedOut. A successful login resets the count via ResetAccessFailedCountAsync.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Issuing and Validating JWTs",
"Issue signed JWTs with JsonWebTokenHandler, configure JwtBearer middleware to validate them, understand every TokenValidationParameters field, and handle 401 vs 403 correctly.",
[("JwtBearer middleware","ASP.NET Core middleware (<code>AddAuthentication().AddJwtBearer()</code>) that extracts, validates, and sets the <code>ClaimsPrincipal</code> for each request."),
("JsonWebTokenHandler","The modern (.NET 6+) handler for creating and reading JWTs; faster than the legacy JwtSecurityTokenHandler."),
("JwtSecurityTokenHandler","The legacy handler; still works but Microsoft recommends JsonWebTokenHandler for new code."),
("TokenValidationParameters","A class holding all validation rules: issuer, audience, signing key, clock skew, lifetime."),
("ClockSkew","The allowed time difference between servers. Default is 5 minutes; set to <code>TimeSpan.Zero</code> for stricter tests."),
("SecurityTokenDescriptor","Describes the token to issue: subject (claims), issuer, audience, expiry, signing credentials."),
("SigningCredentials","Wraps the key and algorithm used to sign: <code>new SigningCredentials(key, SecurityAlgorithms.HmacSha256)</code>."),
("SymmetricSecurityKey","A key created from a byte array; use a secret of 256+ bits for HS256."),
("RequireAuthorization","Extension on <code>IEndpointConventionBuilder</code>: requires auth on that route/group."),
("401 Unauthorized","The request has no valid credentials — not authenticated."),
("403 Forbidden","The user is authenticated but not authorised for this resource."),
("User-secrets","<code>dotnet user-secrets set Jwt:Key &quot;...&quot;</code> — keeps secrets out of source control in development.")],
["<code>RequireAuthorization()</code> causes a 401 when no token is present. A valid token with wrong role causes 403.",
"Always validate issuer and audience in production — a token from a different service must not work on yours.",
"<code>ClockSkew</code> defaults to 5 minutes; set it to <code>TimeSpan.Zero</code> in tests to catch off-by-one errors.",
"The JWT signing key must be at least 256 bits (32 bytes) for HS256. A short key will throw a runtime exception.",
"Use <code>dotnet user-secrets</code> in development; use environment variables or Azure Key Vault in production. Never commit keys.",
"<code>JsonWebTokenHandler</code> is recommended over <code>JwtSecurityTokenHandler</code> for new code (.NET 6+)."],
f'''
<h3>1. Storing the signing key in user-secrets</h3>
{C(r"""
# Run once per developer machine (inside the project directory)
dotnet user-secrets init
dotnet user-secrets set "Jwt:Key"      "ugaav-super-secret-key-must-be-32chars+"
dotnet user-secrets set "Jwt:Issuer"   "ugaav-auth"
dotnet user-secrets set "Jwt:Audience" "ugaav-api"

# In production use environment variables or Azure Key Vault — NEVER commit to git
# ASPNETCORE_Jwt__Key=...
""", lang="bash")}
{C(r"""
// appsettings.json (non-secret defaults only — do NOT put the key here)
{{
  "Jwt": {{
    "Issuer":          "ugaav-auth",
    "Audience":        "ugaav-api",
    "AccessTokenMins": 15,
    "RefreshTokenDays": 7
  }}
}}
""", "appsettings.json (excerpt)", lang="json")}

<h3>2. Registering JwtBearer in Program.cs</h3>
{C(r"""
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using System.Text;

// --- in builder.Services ---
var jwtKey = builder.Configuration["Jwt:Key"]
    ?? throw new InvalidOperationException("Jwt:Key not configured");

builder.Services.AddAuthentication(opt =>
{
    opt.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    opt.DefaultChallengeScheme    = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(opt =>
{
    opt.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer           = true,
        ValidIssuer              = builder.Configuration["Jwt:Issuer"],

        ValidateAudience         = true,
        ValidAudience            = builder.Configuration["Jwt:Audience"],

        ValidateLifetime         = true,
        ClockSkew                = TimeSpan.Zero,   // no grace period — expiry is exact

        ValidateIssuerSigningKey = true,
        IssuerSigningKey         = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
    };
});

builder.Services.AddAuthorization();

// --- in app (middleware order matters!) ---
app.UseAuthentication();   // must be before UseAuthorization
app.UseAuthorization();
""", "Program.cs — JWT setup")}

<h3>3. TokenService — issuing JWTs</h3>
{C(r"""
// Services/TokenService.cs
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;
using AuthService.Models;

namespace AuthService.Services;

public interface ITokenService
{
    string CreateAccessToken(ApplicationUser user, IEnumerable<string> roles);
    string CreateRefreshTokenValue();   // secure random string — stored in DB (Thu)
}

public class TokenService(IConfiguration cfg) : ITokenService
{
    private readonly string _key      = cfg["Jwt:Key"] ?? throw new InvalidOperationException("Jwt:Key missing");
    private readonly string _issuer   = cfg["Jwt:Issuer"] ?? "ugaav-auth";
    private readonly string _audience = cfg["Jwt:Audience"] ?? "ugaav-api";
    private readonly int    _minutes  = int.TryParse(cfg["Jwt:AccessTokenMins"], out var m) ? m : 15;

    public string CreateAccessToken(ApplicationUser user, IEnumerable<string> roles)
    {
        var claims = new List<Claim>
        {
            new(JwtRegisteredClaimNames.Sub,   user.Id),
            new(JwtRegisteredClaimNames.Email, user.Email!),
            new(JwtRegisteredClaimNames.Jti,   Guid.NewGuid().ToString()),  // unique token ID
            new("name",                         user.FullName),
        };
        // Add a claim per role — the [Authorize(Roles="Admin")] attribute reads these
        foreach (var role in roles)
            claims.Add(new Claim(ClaimTypes.Role, role));

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_key));
        var descriptor = new SecurityTokenDescriptor
        {
            Subject            = new ClaimsIdentity(claims),
            Issuer             = _issuer,
            Audience           = _audience,
            Expires            = DateTime.UtcNow.AddMinutes(_minutes),
            SigningCredentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256)
        };

        var handler = new JsonWebTokenHandler();          // modern handler (.NET 6+)
        return handler.CreateToken(descriptor);            // returns the token string
    }

    public string CreateRefreshTokenValue() =>
        Convert.ToBase64String(System.Security.Cryptography.RandomNumberGenerator.GetBytes(64));
}
""", "Services/TokenService.cs")}

<h3>4. Reading claims inside a controller</h3>
{C(r"""
[ApiController]
[Route("api/[controller]")]
public class MeController(UserManager<ApplicationUser> um) : ControllerBase
{
    [HttpGet]
    [Authorize]                              // 401 if no valid token
    public async Task<IActionResult> Get()
    {
        // User is a ClaimsPrincipal set by JwtBearer middleware
        string userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        //  or:  User.FindFirstValue(JwtRegisteredClaimNames.Sub)!;

        var user = await um.FindByIdAsync(userId);
        return Ok(new { user!.Email, user.FullName, Roles = User.FindAll(ClaimTypes.Role).Select(c => c.Value) });
    }
}
""", "Controllers/MeController.cs")}

<h3>5. Protecting routes — 401 vs 403</h3>
{C(r"""
// Global default: require auth on all routes except those you opt out
// Or opt-in per route/group:

// 1. Attribute on a controller
[Authorize]                              // any authenticated user
[Authorize(Roles = "Admin")]             // only Admin role → 403 if wrong role

// 2. Minimal API route groups
var auth = app.MapGroup("/api").RequireAuthorization();
var admin = app.MapGroup("/api/admin").RequireAuthorization(p => p.RequireRole("Admin"));

auth.MapGet("/products", GetProducts);
admin.MapGet("/users", GetAllUsers);

// 3. AllowAnonymous overrides for specific routes inside a protected group
auth.MapPost("/auth/login", Login).AllowAnonymous();
""", "Program.cs — route authorisation")}
{table(["Code","When it fires","Cause"],[
["401 Unauthorized","No token / invalid token / expired token","Not authenticated at all"],
["403 Forbidden","Valid token, but missing role or policy","Authenticated, insufficient permissions"]])}
{tip("JwtBearer returns 401 by default when validation fails. If you want a custom response body, hook <code>opt.Events.OnChallenge</code> and <code>opt.Events.OnForbidden</code>.")}

<h3>6. Quick validation test with curl</h3>
{C(r"""
# 1. Login to get a token
TOKEN=$(curl -s -X POST https://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{{"email":"priya@ugaav.in","password":"Secret@123"}}' \
  | jq -r '.accessToken')

# 2. Call a protected endpoint
curl -s https://localhost:5001/api/me \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. No token → 401
curl -s -o /dev/null -w "%{{http_code}}" https://localhost:5001/api/me
# → 401

# 4. Farmer token hitting Admin endpoint → 403
curl -s -o /dev/null -w "%{{http_code}}" https://localhost:5001/api/admin/users \
  -H "Authorization: Bearer $FARMER_TOKEN"
# → 403
""", lang="bash")}
''',
["Setting <code>ClockSkew = TimeSpan.FromMinutes(5)</code> explicitly (the default) and not realising tokens remain valid 5 minutes after <code>exp</code>.",
"Forgetting <code>app.UseAuthentication()</code> before <code>app.UseAuthorization()</code> — all requests appear unauthenticated.",
"Using a signing key shorter than 32 bytes for HS256 — a <code>SecurityTokenInvalidSigningKeyException</code> at runtime.",
"Not storing the signing key in user-secrets/env-var — commit to git once and you must rotate the key.",
"Setting <code>ValidateAudience = false</code> in production — a token from another service works on yours.",
"Confusing <code>ClaimTypes.NameIdentifier</code> (URN) with <code>JwtRegisteredClaimNames.Sub</code> — both refer to the subject but as different claim type strings."],
("40 min", ["Implement <code>TokenService.CreateAccessToken</code> and register it with <code>AddScoped&lt;ITokenService, TokenService&gt;()</code>.",
"Add the JwtBearer configuration to Program.cs and verify a protected endpoint returns 401 without a token.",
"Decode a token you issued with <code>https://jwt.io</code> and confirm all expected claims are present."]),
[("What is the difference between JsonWebTokenHandler and JwtSecurityTokenHandler?","JsonWebTokenHandler is the modern replacement; it is faster, returns a string from CreateToken directly, and is recommended for all new code. JwtSecurityTokenHandler is legacy but still functional."),
("What does ClockSkew do?","It adds a time window around the token expiry to tolerate clock drift between servers. Default is 5 minutes, meaning a token is accepted for 5 minutes after its stated exp. Setting it to TimeSpan.Zero makes expiry exact."),
("Why should ValidateIssuer and ValidateAudience both be true in production?","Issuer check ensures the token was issued by your auth service. Audience check ensures it was intended for this API. Without both, any valid JWT from any service in your infrastructure could be used on any other.")],
[("Basic","What middleware order is required for JWT auth in ASP.NET Core?","app.UseAuthentication() must come before app.UseAuthorization(). Authentication sets the ClaimsPrincipal; authorization evaluates it. The order is enforced at runtime — reversing them means every request appears unauthenticated."),
("Basic","How does RequireAuthorization() differ from [Authorize] on a controller?","[Authorize] is an attribute; RequireAuthorization() is an extension method on IEndpointConventionBuilder, used for Minimal APIs and route groups. Both enforce the same policy engine; the syntax differs by programming model."),
("Basic","How do you read the current user's ID inside a controller?","User.FindFirstValue(ClaimTypes.NameIdentifier) or User.FindFirstValue(JwtRegisteredClaimNames.Sub). JwtBearer maps the sub claim to NameIdentifier by default."),
("Intermediate","How do you return a custom 401 response body from JwtBearer?","Hook opt.Events.OnChallenge in AddJwtBearer. Set context.HandleResponse() to suppress the default, then write your JSON body with context.Response.WriteAsJsonAsync()."),
("Intermediate","A token was valid when issued but the user's role was changed in the DB. How do you handle this?","Short-lived access tokens (15 min) mean the stale role data expires quickly. For immediate revocation, store a user version number as a claim and invalidate tokens whose version doesn't match the DB — or use opaque tokens with a database lookup on every request."),
("Advanced","Explain the TokenValidationParameters fields that defend against token substitution attacks.","ValidateIssuer ensures the token came from your auth service (not a different one that also uses HS256). ValidateAudience ensures it was intended for your API (not reused from another service). ValidateIssuerSigningKey ensures the signature was produced with your key. All three together make a token non-transferable across services.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Refresh Tokens, Password Reset and Account Lockout",
"Issue short-lived access tokens paired with long-lived refresh tokens, implement rotation with reuse detection, design a password-reset flow, and configure lockout correctly.",
[("Refresh token","A long-lived opaque random string that lets a client get a new access token without re-entering credentials."),
("Token rotation","Issuing a brand-new refresh token every time the old one is used, invalidating the old one."),
("Reuse detection","Detecting when a refresh token that was already rotated (replaced) is used again — a sign of theft — and revoking the entire refresh-token chain."),
("Token family / chain","A set of refresh tokens linked by <code>ReplacedBy</code> that all trace back to one original login."),
("PBKDF2","Password-Based Key Derivation Function 2; used by ASP.NET Core Identity for password hashing."),
("Password reset flow","User requests reset → email with signed token (Identity DataProtectionTokenProvider) → user submits new password with token → token validated and invalidated."),
("Lockout","ASP.NET Core Identity's built-in brute-force protection: N failed logins → account locked for T minutes."),
("AccessFailedCount","Column on AspNetUsers tracking consecutive login failures, reset on success."),
("LockoutEnd","Nullable DateTimeOffset on AspNetUsers; if set and in the future, sign-in returns IsLockedOut."),
("RefreshToken (table)","Your own table: Token (hashed), UserId, ExpiresAt, RevokedAt, ReplacedBy, CreatedAt.")],
["Store the <b>hash</b> of the refresh token in the database — not the plain value. If the DB is compromised, tokens are still useless.",
"Rotate on every use. The old token is immediately marked <code>ReplacedBy = newTokenId</code>.",
"Reuse detection: if a token that was already replaced is presented, revoke the entire chain — it means one copy was stolen.",
"Logout = revoke the refresh token in the DB (and all its chain if you like). The access token expires naturally.",
"Password reset tokens from Identity are single-use and time-limited (default 1 day) — do not roll your own.",
"Lockout applies to the sign-in action, not token refresh. Refresh reuse detection is a separate revocation mechanism."],
f'''
<h3>1. RefreshToken entity</h3>
{C(r"""
// Models/RefreshToken.cs
namespace AuthService.Models;

public class RefreshToken
{{
    public int    Id          {{ get; set; }}
    public string UserId      {{ get; set; }} = string.Empty;   // FK → AspNetUsers.Id
    public string Token       {{ get; set; }} = string.Empty;   // HASHED value stored here
    public string? ReplacedBy {{ get; set; }}                    // hash of the successor token
    public DateTime ExpiresAt {{ get; set; }}
    public DateTime CreatedAt {{ get; set; }} = DateTime.UtcNow;
    public DateTime? RevokedAt {{ get; set; }}

    public bool IsExpired  => DateTime.UtcNow >= ExpiresAt;
    public bool IsRevoked  => RevokedAt is not null;
    public bool IsActive   => !IsExpired && !IsRevoked;
}}
""", "Models/RefreshToken.cs")}

<h3>2. Storing and hashing refresh tokens</h3>
{C(r"""
// Services/TokenService.cs (additions)
using System.Security.Cryptography;

public string CreateRefreshTokenValue() =>
    Convert.ToBase64String(RandomNumberGenerator.GetBytes(64));  // 64 raw bytes → 88 char base64

public string HashToken(string tokenValue) =>
    Convert.ToBase64String(SHA256.HashData(Encoding.UTF8.GetBytes(tokenValue)));

// In your auth service:
string rawToken = tokenService.CreateRefreshTokenValue();      // send this to the client
string hashed   = tokenService.HashToken(rawToken);            // store THIS in the DB

var refreshToken = new RefreshToken
{{
    UserId    = user.Id,
    Token     = hashed,
    ExpiresAt = DateTime.UtcNow.AddDays(int.Parse(cfg["Jwt:RefreshTokenDays"] ?? "7"))
}};
await db.RefreshTokens.AddAsync(refreshToken);
await db.SaveChangesAsync();
""", "Services/TokenService.cs (additions)")}
{tip("SHA-256 is fine for hashing refresh tokens because they are long random values (high entropy). Do <b>not</b> use SHA-256 to hash passwords — use PBKDF2 / bcrypt / Argon2.")}

<h3>3. Refresh flow with rotation and reuse detection</h3>
{C(r"""
// Services/AuthService.cs (refresh logic)
public async Task<AuthResult> RefreshAsync(string rawRefreshToken)
{{
    string hashed = tokenService.HashToken(rawRefreshToken);

    // Find the token in the DB (active or not — we need it even if revoked for reuse detection)
    var stored = await db.RefreshTokens
        .FirstOrDefaultAsync(r => r.Token == hashed);

    if (stored is null)
        return AuthResult.Fail("Invalid refresh token");

    if (stored.IsRevoked)
    {{
        // Token was already replaced/revoked — REUSE DETECTED
        // Revoke all tokens in the chain (tokens where ReplacedBy traces back to this user)
        await RevokeChainAsync(stored.UserId);
        return AuthResult.Fail("Refresh token reuse detected — all sessions revoked");
    }}

    if (stored.IsExpired)
        return AuthResult.Fail("Refresh token expired — please log in again");

    var user  = await userManager.FindByIdAsync(stored.UserId);
    if (user is null) return AuthResult.Fail("User not found");

    var roles       = await userManager.GetRolesAsync(user);
    string newAccess = tokenService.CreateAccessToken(user, roles);

    // Rotate: create a new refresh token and link the old one to it
    string newRaw    = tokenService.CreateRefreshTokenValue();
    string newHashed = tokenService.HashToken(newRaw);

    stored.RevokedAt  = DateTime.UtcNow;      // mark old token as used/replaced
    stored.ReplacedBy = newHashed;

    var newToken = new RefreshToken
    {{
        UserId    = user.Id,
        Token     = newHashed,
        ExpiresAt = stored.ExpiresAt          // keep the same expiry (sliding window is a design choice)
    }};
    db.RefreshTokens.Update(stored);
    await db.RefreshTokens.AddAsync(newToken);
    await db.SaveChangesAsync();

    return AuthResult.Ok(newAccess, newRaw);   // return the RAW token to the client
}}

private async Task RevokeChainAsync(string userId)
{{
    var allTokens = await db.RefreshTokens
        .Where(r => r.UserId == userId && r.RevokedAt == null)
        .ToListAsync();
    foreach (var t in allTokens) t.RevokedAt = DateTime.UtcNow;
    await db.SaveChangesAsync();
}}
""", "Services/AuthService.cs — refresh")}

<h3>4. Logout</h3>
{C(r"""
// POST /api/auth/logout  (requires [Authorize])
public async Task<IActionResult> Logout([FromBody] string rawRefreshToken)
{{
    string hashed = tokenService.HashToken(rawRefreshToken);
    var stored = await db.RefreshTokens.FirstOrDefaultAsync(r => r.Token == hashed);

    if (stored is not null && stored.IsActive)
    {{
        stored.RevokedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
    }}
    // Access token expires naturally (can't revoke without a token blacklist or opaque tokens)
    return Ok(new {{ message = "Logged out" }});
}}
""", "Controllers/AuthController.cs — logout")}

<h3>5. Password reset with Identity tokens</h3>
{C(r"""
// POST /api/auth/forgot-password
public async Task<IActionResult> ForgotPassword([FromBody] ForgotPasswordDto dto)
{{
    var user = await userManager.FindByEmailAsync(dto.Email);
    if (user is null) return Ok(); // don't reveal whether the email is registered

    string token = await userManager.GeneratePasswordResetTokenAsync(user);
    // token is URL-safe; send in an email link:
    // https://app.ugaav.in/reset-password?token=<WebUtility.UrlEncode(token)>&email=<email>

    // TODO: send email via IEmailSender (beyond scope today — use a background job in Week 21)
    return Ok(new {{ message = "If that email exists, a reset link has been sent" }});
}}

// POST /api/auth/reset-password
public async Task<IActionResult> ResetPassword([FromBody] ResetPasswordDto dto)
{{
    var user = await userManager.FindByEmailAsync(dto.Email);
    if (user is null) return BadRequest();

    var result = await userManager.ResetPasswordAsync(user, dto.Token, dto.NewPassword);
    if (!result.Succeeded) return BadRequest(result.Errors);

    // Also revoke all refresh tokens on password reset
    await RevokeChainAsync(user.Id);
    return Ok(new {{ message = "Password reset successful" }});
}}
""", "Controllers/AuthController.cs — reset")}
{table(["Step","Detail"],[
["Generate token","<code>userManager.GeneratePasswordResetTokenAsync(user)</code> — uses DataProtection, time-limited"],
["Send email","Include token (URL-encoded) + email in the reset link"],
["Validate & apply","<code>userManager.ResetPasswordAsync(user, token, newPassword)</code> — single use; throws if already used"],
["Revoke refresh tokens","Invalidate all sessions so stolen sessions can't continue after a password change"]])}

<h3>6. Lockout flow</h3>
{table(["Event","Identity behaviour"],[
["Wrong password (attempt 1–4)","AccessFailedCount++; locked = false"],
["Wrong password (attempt 5)","AccessFailedCount = 5 ≥ MaxFailedAccessAttempts; LockoutEnd = now + 10 min"],
["Login attempt while locked","SignInResult.IsLockedOut = true; don't reveal remaining time (enumeration risk)"],
["Correct password after lockout expires","AccessFailedCount reset to 0; login succeeds"],
["Correct password before lockout expires","Still locked — correct password doesn't unlock early"]])}
''',
["Storing the raw refresh token value in the database instead of its hash.",
"Not detecting token reuse — stolen refresh tokens can be used indefinitely if rotation but no reuse detection.",
"Reusing the same expiry on the new token vs resetting it — decide deliberately; both are valid designs.",
"Not revoking all sessions on password reset — a stolen refresh token remains valid.",
"Revealing whether an email is registered in the forgot-password endpoint — always return 200.",
"Calling Identity's ResetPasswordAsync with the same token twice — the second call will fail because Identity marks it used."],
("45 min", ["Implement the RefreshToken entity and add it to AppDbContext with an index on the Token column.",
"Implement AuthService.RefreshAsync with rotation and reuse detection (as above).",
"Test reuse detection: use a refresh token, then try to use the original again — confirm all tokens for the user are revoked."]),
[("Why store a hash of the refresh token?","If the database is compromised, the attacker gets hashes, not the raw tokens. Without the raw value they can't present a valid token. (This is the same reason passwords are hashed.)"),
("What is rotation and reuse detection?","Rotation: each use of a refresh token issues a new one and revokes the old. Reuse detection: if the revoked token is used again, it means a copy was stolen — revoke the entire chain to log the attacker out."),
("How does password reset differ from a regular token exchange?","Identity generates a DataProtection-backed, time-limited, single-use token and ties it to the user's current password hash. If the password changes, all outstanding reset tokens are automatically invalidated.")],
[("Basic","What is a refresh token and why is the access token kept short-lived?","A refresh token is a long-lived opaque credential used to obtain new access tokens. Access tokens are kept short-lived (15 min) to limit the damage of theft — they expire quickly. The refresh token allows silent re-auth without re-entering credentials, but it can be revoked from the server."),
("Basic","What is the minimum you must store for a refresh token in the database?","The hashed token value, the user ID it belongs to, and an expiry. You should also store RevokedAt and ReplacedBy to support rotation and reuse detection."),
("Intermediate","Describe the refresh token rotation and reuse detection algorithm.","On every use: (1) look up the hash in the DB. (2) If revoked/replaced → reuse detected → revoke entire chain. (3) If expired → reject. (4) Otherwise: mark old token RevokedAt, create a new token, link old.ReplacedBy = newHash, return new raw token + new access token."),
("Intermediate","How should you handle logout with JWTs?","Revoke the refresh token in the database so it can't be used to mint new access tokens. The current access token cannot be revoked without a blacklist (e.g. Redis), but its short lifetime (15 min) limits the window. For high-security needs, maintain a token blacklist or use opaque tokens."),
("Intermediate","Why should you revoke all sessions when a user resets their password?","A password reset usually means the account was compromised. Any active refresh token from before the reset could still be in an attacker's hands. Revoking all tokens forces every device to re-authenticate with the new password."),
("Advanced","Compare stateless JWTs versus stateful opaque tokens for a high-security fintech API.","Stateless JWTs: no DB lookup per request, horizontally scalable, but can't be revoked until expiry (unless you add a blacklist). Opaque tokens: validated by the auth server each request (DB lookup or cache), instantly revocable, but adds latency and a centralised component. Hybrid approach: short-lived JWTs for performance + a Redis revocation list for immediate invalidation on logout/compromise.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Authorisation — Roles, Policies and Resource-Based Checks",
"Go beyond [Authorize(Roles=...)] with custom requirements, handlers, and resource-based authorisation using IAuthorizationService.",
[("Role-based authorisation","Granting access based on membership in a named role, e.g. <code>[Authorize(Roles = \"Admin\")]</code>."),
("Policy-based authorisation","A named set of requirements registered in DI; more expressive and testable than raw role checks."),
("IAuthorizationRequirement","A marker interface for a requirement data class, e.g. <code>MinimumAgeRequirement(18)</code>."),
("AuthorizationHandler&lt;T&gt;","Evaluates one requirement: calls <code>context.Succeed(requirement)</code> or leaves it pending."),
("IAuthorizationService","Injected service for imperative / resource-based checks inside controllers or services."),
("Resource-based authorisation","Authorising against a specific resource object (e.g. 'can this user edit THIS blog post?')."),
("AuthorizationHandlerContext","Passed to handlers: contains User (ClaimsPrincipal), Requirements, and optional Resource."),
("RequireClaim","Built-in requirement: user must have a specific claim (optionally with a specific value)."),
("RequireRole","Built-in requirement inside a policy: equivalent to [Authorize(Roles=...)] but composable."),
("Fallback policy","A policy applied to every endpoint that hasn't set its own. Set with <code>options.FallbackPolicy</code>.")],
["Policies are composable — one policy can require both a role AND a minimum claim value.",
"An AuthorizationHandler that doesn't call <code>Succeed</code> or <code>Fail</code> just leaves the requirement pending; other handlers for the same requirement may still succeed it.",
"Calling <code>context.Fail()</code> short-circuits — even if another handler would succeed, the check fails.",
"Resource-based checks CANNOT use <code>[Authorize]</code> attributes because the resource isn't available at attribute-evaluation time — use <code>IAuthorizationService.AuthorizeAsync</code> in the action.",
"Set a fallback policy of <code>AuthorizationPolicies.RequireAuthenticatedUser()</code> to protect every endpoint by default; then use <code>[AllowAnonymous]</code> selectively.",
"Roles are just claims — <code>ClaimTypes.Role</code> — so role-based and claim-based auth are the same system."],
f'''
<h3>1. Role-based authorisation (simplest form)</h3>
{C(r"""
// Register policies in Program.cs
builder.Services.AddAuthorization(opt =>
{{
    opt.AddPolicy("AdminOnly",   p => p.RequireRole("Admin"));
    opt.AddPolicy("FarmerOrAdmin", p => p.RequireRole("Farmer", "Admin"));  // OR logic

    // Require that the JWT has a "verified" claim with value "true"
    opt.AddPolicy("Verified",    p => p.RequireClaim("verified", "true"));

    // Require both a role AND a claim
    opt.AddPolicy("VerifiedFarmer", p =>
        p.RequireRole("Farmer").RequireClaim("verified", "true"));

    // Default policy for all [Authorize] attributes without a named policy
    opt.DefaultPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();
}});
""", "Program.cs — policies")}
{C(r"""
[Authorize(Policy = "AdminOnly")]
[HttpGet("admin/users")]
public IActionResult AdminOnlyEndpoint() => Ok("admin area");

[Authorize(Policy = "FarmerOrAdmin")]
[HttpPost("orders")]
public IActionResult PlaceOrder() => Ok("order placed");
""", "example usage")}

<h3>2. Custom requirement and handler</h3>
{C(r"""
// Auth/Requirements/MinFarmSizeRequirement.cs
using Microsoft.AspNetCore.Authorization;

namespace AuthService.Auth;

// 1. Requirement — just data
public record MinFarmSizeRequirement(int MinAcres) : IAuthorizationRequirement;

// 2. Handler — evaluates the requirement
public class MinFarmSizeHandler : AuthorizationHandler<MinFarmSizeRequirement>
{{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        MinFarmSizeRequirement requirement)
    {{
        // Read a custom claim set during login: "farm_acres": "50"
        var acresClaim = context.User.FindFirstValue("farm_acres");
        if (acresClaim is not null && int.TryParse(acresClaim, out int acres) && acres >= requirement.MinAcres)
            context.Succeed(requirement);

        // Don't call Fail() — let other handlers try if present
        return Task.CompletedTask;
    }}
}}
""", "Auth/MinFarmSizeHandler.cs")}
{C(r"""
// Register in Program.cs
builder.Services.AddSingleton<IAuthorizationHandler, MinFarmSizeHandler>();
builder.Services.AddAuthorization(opt =>
{{
    opt.AddPolicy("LargeFarm", p => p.Requirements.Add(new MinFarmSizeRequirement(10)));
    opt.AddPolicy("EnterpriseFarm", p => p.Requirements.Add(new MinFarmSizeRequirement(100)));
}});
""", "Program.cs — custom policy")}

<h3>3. Resource-based authorisation (author or admin)</h3>
<p>Can a user edit a farm listing? They are allowed if they are the owner of that listing OR an Admin.
This cannot be checked via <code>[Authorize]</code> because we need the actual DB record.</p>
{C(r"""
// Auth/Requirements/FarmListingOperations.cs
using Microsoft.AspNetCore.Authorization.Infrastructure;

namespace AuthService.Auth;

public static class FarmListingOperations
{{
    public static OperationAuthorizationRequirement Edit   = new() {{ Name = "Edit" }};
    public static OperationAuthorizationRequirement Delete = new() {{ Name = "Delete" }};
}}

// Auth/Handlers/FarmListingAuthHandler.cs
public class FarmListingAuthHandler
    : AuthorizationHandler<OperationAuthorizationRequirement, FarmListing>
{{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        OperationAuthorizationRequirement requirement,
        FarmListing resource)
    {{
        bool isAdmin = context.User.IsInRole("Admin");
        string? userId = context.User.FindFirstValue(ClaimTypes.NameIdentifier);
        bool isOwner = resource.OwnerId == userId;

        if (isAdmin || isOwner)
            context.Succeed(requirement);

        return Task.CompletedTask;
    }}
}}
""", "Auth/FarmListingAuthHandler.cs")}
{C(r"""
// In a controller — inject IAuthorizationService
public class FarmListingsController(
    IAuthorizationService authService,
    FarmListingRepository repo) : ControllerBase
{{
    [HttpPut("{{id}}")]
    [Authorize]
    public async Task<IActionResult> Edit(int id, [FromBody] EditFarmDto dto)
    {{
        var listing = await repo.GetByIdAsync(id);
        if (listing is null) return NotFound();

        // Resource-based check: pass the entity as the resource
        var authResult = await authService.AuthorizeAsync(User, listing, FarmListingOperations.Edit);
        if (!authResult.Succeeded) return Forbid();   // 403

        listing.ApplyEdit(dto);
        await repo.SaveAsync();
        return Ok(listing);
    }}
}}
""", "Controllers/FarmListingsController.cs")}

<h3>4. Policies on Minimal API route groups</h3>
{C(r"""
var api    = app.MapGroup("/api").RequireAuthorization();
var admin  = app.MapGroup("/api/admin").RequireAuthorization("AdminOnly");
var farmer = app.MapGroup("/api/farmer").RequireAuthorization("FarmerOrAdmin");

api.MapGet("/me", (ClaimsPrincipal user) => user.FindFirstValue(JwtRegisteredClaimNames.Sub));
admin.MapGet("/users", (UserManager<ApplicationUser> um) => um.Users.Select(u => u.Email));
farmer.MapPost("/listings", (FarmListingDto dto) => Results.Created("/api/farmer/listings/1", dto));
""", "Program.cs — Minimal API groups")}

<h3>5. Fallback policy — secure by default</h3>
{C(r"""
builder.Services.AddAuthorization(opt =>
{{
    // Every endpoint requires authentication UNLESS it has [AllowAnonymous] or .AllowAnonymous()
    opt.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();
}});

// Now explicitly open public endpoints:
app.MapPost("/api/auth/login",         Login).AllowAnonymous();
app.MapPost("/api/auth/register",      Register).AllowAnonymous();
app.MapPost("/api/auth/refresh",       Refresh).AllowAnonymous();
app.MapPost("/api/auth/forgot-password", ForgotPassword).AllowAnonymous();
""", "Program.cs — secure by default")}
''',
["Using <code>[Authorize(Roles = \"Admin,Farmer\")]</code> — this requires BOTH roles (AND logic). For OR use a policy with <code>RequireRole(\"Admin\", \"Farmer\")</code>.",
"Calling <code>context.Fail()</code> in a handler when you just mean 'I can't decide' — Fail is a veto; leave it pending instead.",
"Injecting scoped services (like DbContext) into a singleton AuthorizationHandler — register the handler as scoped instead.",
"Forgetting to register the custom handler with <code>AddSingleton&lt;IAuthorizationHandler, MyHandler&gt;()</code>.",
"Trying to use [Authorize] for resource-based checks — it evaluates before the action runs and has no access to the resource."],
("40 min", ["Implement the <code>MinFarmSizeHandler</code>, register it, and add a 'farm_acres' claim during login to test it.",
"Add a FarmListing entity, the <code>FarmListingAuthHandler</code>, and test that only the owner and Admin can edit.",
"Set a fallback policy and confirm that forgetting [AllowAnonymous] on the login endpoint returns 401."]),
[("What is the difference between a role and a policy?","A role is a string claim (ClaimTypes.Role) on the user. A policy is a named set of requirements registered in DI; it can require roles, claims, custom logic, or any combination. Policies are more composable and unit-testable."),
("When must you use IAuthorizationService instead of [Authorize]?","When the check depends on a specific resource (e.g. 'can this user edit this listing?'). The [Authorize] attribute evaluates before the action body, so the resource object isn't loaded yet."),
("What does context.Fail() do in a handler?","It immediately signals failure — no other handler for any requirement can succeed the check. Use it only for explicit denial (e.g. banned user). If you simply can't satisfy the requirement, leave it pending (don't call Succeed or Fail).")],
[("Basic","What is a policy in ASP.NET Core authorization?","A named, registered set of requirements. Applied with [Authorize(Policy=\"Name\")] or RequireAuthorization(\"Name\"). You register policies in AddAuthorization and they can combine role checks, claim checks, and custom logic."),
("Basic","How do you require that a user is in EITHER of two roles?","Use a policy: p.RequireRole(\"Admin\", \"Farmer\") — passing multiple role names to RequireRole means the user must be in at least one. [Authorize(Roles = \"Admin,Farmer\")] also works (comma = OR for roles)."),
("Intermediate","Explain the lifecycle of an IAuthorizationRequirement being evaluated.","AuthorizationService collects all handlers registered for the requirement type. It calls each handler's HandleRequirementAsync. If any handler calls Succeed and none calls Fail, the requirement passes. If all handlers leave it pending (neither Succeed nor Fail), it fails. A single Fail vetoes all."),
("Intermediate","What is an OperationAuthorizationRequirement?","A built-in IAuthorizationRequirement with a Name property (e.g. \"Edit\", \"Delete\"). Handlers are written against OperationAuthorizationRequirement and inspect the Name property, allowing one handler class to cover multiple operations on the same resource type."),
("Intermediate","How do you unit-test a custom AuthorizationHandler?","Create a DefaultAuthorizationHandlerContext with a test ClaimsPrincipal, the requirement, and optionally a resource. Call HandleRequirementAsync directly. Assert context.HasSucceeded or context.HasFailed."),
("Advanced","Describe a defence-in-depth authorisation design for a multi-tenant SaaS API.","(1) Authentication: validate JWT, ensure correct issuer/audience. (2) Global fallback policy: require authenticated user. (3) Role policy: CoarseRoute-level (Admin, Tenant, User). (4) Resource policy: row-level check that TenantId on the resource matches the claim in the token. (5) Logging: log every 403 for anomaly detection. This prevents both horizontal (another user's data) and vertical (insufficient role) access.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "AuthService — Full Working Implementation",
"Build the AuthService micro-project end to end: register, login, refresh (with rotation and reuse detection), logout, /me, admin user list, and change-password, then walk through a complete curl lifecycle.",
[("AuthService","A standalone ASP.NET Core Web API that owns identity: registration, login, token issuance, refresh, logout."),
("TokenService","Thin service responsible only for JWT creation and refresh-token value generation/hashing."),
("Shared validation","A FluentValidation (or DataAnnotation) validator shared across DTOs to enforce password rules consistently."),
("curl lifecycle","A sequence of curl commands that exercises every auth endpoint end-to-end without a browser.")],
["AuthService is the Week 20 micro-project — it integrates everything from Mon–Fri.",
"Saturday is the full implementation; Sunday adds Blog API security, try-to-break tests and the week checklist.",
"All database work requires SQL Server 2022 (Docker) — the sandbox can build but not run migrations.",
"You cannot run EF Core migrations offline — ensure Docker is running before Saturday's work."],
f'''
<h3>Project scaffold</h3>
{C(r"""
# Terminal
dotnet new webapi -n AuthService --use-controllers
cd AuthService
dotnet add package Microsoft.AspNetCore.Identity.EntityFrameworkCore --version 8.0.0
dotnet add package Microsoft.EntityFrameworkCore.SqlServer --version 8.0.0
dotnet add package Microsoft.EntityFrameworkCore.Design --version 8.0.0
dotnet add package Microsoft.AspNetCore.Authentication.JwtBearer --version 8.0.0

# Docker: SQL Server 2022
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourStrong@Passw0rd" \
  -p 1433:1433 --name sqlserver -d mcr.microsoft.com/mssql/server:2022-latest

# User secrets
dotnet user-secrets init
dotnet user-secrets set "Jwt:Key"      "ugaav-auth-service-secret-key-32bytesminimum!"
dotnet user-secrets set "Jwt:Issuer"   "ugaav-auth"
dotnet user-secrets set "Jwt:Audience" "ugaav-api"
dotnet user-secrets set "Seed:AdminPassword" "Admin@12345"
dotnet user-secrets set "ConnectionStrings:Default" \
  "Server=localhost,1433;Database=UgaavAuth;User Id=sa;Password=YourStrong@Passw0rd;TrustServerCertificate=True"
""", lang="bash")}

<h3>Folder layout</h3>
{C(r"""
AuthService/
├── Controllers/
│   └── AuthController.cs       ← register, login, refresh, logout, change-password
│   └── MeController.cs         ← GET /api/me (self info)
│   └── AdminController.cs      ← GET /api/admin/users
├── Data/
│   ├── AppDbContext.cs
│   └── DbSeeder.cs
├── Models/
│   ├── ApplicationUser.cs
│   └── RefreshToken.cs
├── Services/
│   ├── ITokenService.cs
│   ├── TokenService.cs
│   └── IAuthService.cs
│   └── AuthService.cs          ← orchestrates Identity + TokenService
├── DTOs/
│   ├── RegisterDto.cs
│   ├── LoginDto.cs
│   ├── RefreshDto.cs
│   ├── ChangePasswordDto.cs
│   └── AuthResult.cs
├── Auth/                        ← requirements and handlers (Fri content)
│   ├── MinFarmSizeHandler.cs
│   └── FarmListingAuthHandler.cs
├── appsettings.json
└── Program.cs
""", lang="text")}

<h3>DTOs</h3>
{C(r"""
// DTOs/RegisterDto.cs
using System.ComponentModel.DataAnnotations;
namespace AuthService.DTOs;

public record RegisterDto(
    [Required, EmailAddress]              string Email,
    [Required, MinLength(2), MaxLength(100)] string FullName,
    [Required, MinLength(8)]              string Password
);

// DTOs/LoginDto.cs
public record LoginDto(
    [Required, EmailAddress] string Email,
    [Required]               string Password
);

// DTOs/RefreshDto.cs
public record RefreshDto([Required] string RefreshToken);

// DTOs/ChangePasswordDto.cs
public record ChangePasswordDto(
    [Required] string CurrentPassword,
    [Required, MinLength(8)] string NewPassword
);

// DTOs/AuthResult.cs
public record AuthResult(
    bool   Succeeded,
    string? AccessToken  = null,
    string? RefreshToken = null,
    string? Error        = null
)
{{
    public static AuthResult Ok(string access, string refresh)
        => new(true, access, refresh);
    public static AuthResult Fail(string error)
        => new(false, Error: error);
}}
""", "DTOs/*.cs")}

<h3>AuthService.cs — the core orchestrator</h3>
{C(r"""
// Services/AuthService.cs
using AuthService.Data;
using AuthService.DTOs;
using AuthService.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace AuthService.Services;

public class UgaavAuthService(
    UserManager<ApplicationUser> userManager,
    SignInManager<ApplicationUser> signInManager,
    ITokenService tokenService,
    AppDbContext db)
{
    public async Task<AuthResult> RegisterAsync(RegisterDto dto)
    {
        var user = new ApplicationUser { UserName = dto.Email, Email = dto.Email, FullName = dto.FullName };
        var result = await userManager.CreateAsync(user, dto.Password);
        if (!result.Succeeded)
            return AuthResult.Fail(string.Join("; ", result.Errors.Select(e => e.Description)));

        await userManager.AddToRoleAsync(user, "Farmer");     // default role
        return await IssueTokenPairAsync(user);
    }

    public async Task<AuthResult> LoginAsync(LoginDto dto)
    {
        var user = await userManager.FindByEmailAsync(dto.Email);
        if (user is null) return AuthResult.Fail("Invalid credentials");

        var signIn = await signInManager.CheckPasswordSignInAsync(user, dto.Password, lockoutOnFailure: true);
        if (signIn.IsLockedOut)  return AuthResult.Fail("Account locked — try again later");
        if (!signIn.Succeeded)   return AuthResult.Fail("Invalid credentials");

        return await IssueTokenPairAsync(user);
    }

    public async Task<AuthResult> RefreshAsync(string rawRefreshToken)
    {
        string hashed = tokenService.HashToken(rawRefreshToken);
        var stored    = await db.RefreshTokens.FirstOrDefaultAsync(r => r.Token == hashed);
        if (stored is null) return AuthResult.Fail("Invalid token");

        if (stored.IsRevoked)
        {
            await RevokeChainAsync(stored.UserId);
            return AuthResult.Fail("Token reuse detected — all sessions revoked");
        }
        if (stored.IsExpired) return AuthResult.Fail("Refresh token expired");

        var user  = await userManager.FindByIdAsync(stored.UserId);
        if (user is null) return AuthResult.Fail("User not found");

        // Rotate
        string newRaw    = tokenService.CreateRefreshTokenValue();
        string newHashed = tokenService.HashToken(newRaw);
        stored.RevokedAt  = DateTime.UtcNow;
        stored.ReplacedBy = newHashed;
        db.RefreshTokens.Update(stored);
        db.RefreshTokens.Add(new RefreshToken
        {
            UserId    = user.Id,
            Token     = newHashed,
            ExpiresAt = stored.ExpiresAt
        });
        await db.SaveChangesAsync();

        var roles       = await userManager.GetRolesAsync(user);
        string newAccess = tokenService.CreateAccessToken(user, roles);
        return AuthResult.Ok(newAccess, newRaw);
    }

    public async Task RevokeAsync(string rawRefreshToken)
    {
        string hashed = tokenService.HashToken(rawRefreshToken);
        var stored    = await db.RefreshTokens.FirstOrDefaultAsync(r => r.Token == hashed);
        if (stored is not null && stored.IsActive)
        {
            stored.RevokedAt = DateTime.UtcNow;
            await db.SaveChangesAsync();
        }
    }

    private async Task<AuthResult> IssueTokenPairAsync(ApplicationUser user)
    {
        var roles  = await userManager.GetRolesAsync(user);
        string access  = tokenService.CreateAccessToken(user, roles);
        string rawRefresh = tokenService.CreateRefreshTokenValue();
        db.RefreshTokens.Add(new RefreshToken
        {
            UserId    = user.Id,
            Token     = tokenService.HashToken(rawRefresh),
            ExpiresAt = DateTime.UtcNow.AddDays(7)
        });
        await db.SaveChangesAsync();
        return AuthResult.Ok(access, rawRefresh);
    }

    private async Task RevokeChainAsync(string userId)
    {
        var active = await db.RefreshTokens
            .Where(r => r.UserId == userId && r.RevokedAt == null)
            .ToListAsync();
        foreach (var t in active) t.RevokedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
    }
}
""", "Services/AuthService.cs")}

<h3>AuthController.cs</h3>
{C(r"""
// Controllers/AuthController.cs
using AuthService.DTOs;
using AuthService.Models;
using AuthService.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

namespace AuthService.Controllers;

[ApiController]
[Route("api/auth")]
public class AuthController(
    UgaavAuthService authSvc,
    UserManager<ApplicationUser> userManager) : ControllerBase
{
    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterDto dto)
    {
        var result = await authSvc.RegisterAsync(dto);
        return result.Succeeded ? Ok(result) : BadRequest(new {{ error = result.Error }});
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginDto dto)
    {
        var result = await authSvc.LoginAsync(dto);
        return result.Succeeded ? Ok(result) : Unauthorized(new {{ error = result.Error }});
    }

    [HttpPost("refresh")]
    public async Task<IActionResult> Refresh([FromBody] RefreshDto dto)
    {
        var result = await authSvc.RefreshAsync(dto.RefreshToken);
        return result.Succeeded ? Ok(result) : Unauthorized(new {{ error = result.Error }});
    }

    [Authorize]
    [HttpPost("logout")]
    public async Task<IActionResult> Logout([FromBody] RefreshDto dto)
    {
        await authSvc.RevokeAsync(dto.RefreshToken);
        return Ok(new {{ message = "Logged out" }});
    }

    [Authorize]
    [HttpPost("change-password")]
    public async Task<IActionResult> ChangePassword([FromBody] ChangePasswordDto dto)
    {
        string userId = User.FindFirstValue(System.Security.Claims.ClaimTypes.NameIdentifier)!;
        var user = await userManager.FindByIdAsync(userId);
        var result = await userManager.ChangePasswordAsync(user!, dto.CurrentPassword, dto.NewPassword);
        if (!result.Succeeded) return BadRequest(result.Errors);
        await authSvc.RevokeChainPublic(userId);   // helper that exposes RevokeChainAsync
        return Ok(new {{ message = "Password changed — please log in again" }});
    }
}
""", "Controllers/AuthController.cs")}

<h3>curl lifecycle walkthrough</h3>
{C(r"""
BASE=https://localhost:5001

# 1. Register a new farmer (Rahul Verma, Jaipur)
curl -k -s -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{{"email":"rahul.verma@example.in","fullName":"Rahul Verma","password":"Secure@123"}}' | jq .
# → { "accessToken": "eyJ...", "refreshToken": "abc..." }

ACCESS=$(curl -k -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{{"email":"rahul.verma@example.in","password":"Secure@123"}}' | jq -r '.accessToken')
REFRESH=$(curl -k -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{{"email":"rahul.verma@example.in","password":"Secure@123"}}' | jq -r '.refreshToken')

# 2. Access protected endpoint
curl -k -s $BASE/api/me -H "Authorization: Bearer $ACCESS" | jq .
# → { "email": "rahul.verma@example.in", "fullName": "Rahul Verma", "roles": ["Farmer"] }

# 3. Refresh
NEW=$(curl -k -s -X POST $BASE/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refreshToken\":\"$REFRESH\"}" | jq .)
echo $NEW
# → { "accessToken": "eyJ... (new)", "refreshToken": "xyz... (new, old is now revoked)" }

# 4. Reuse detection: try the OLD refresh token again
curl -k -s -X POST $BASE/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refreshToken\":\"$REFRESH\"}" | jq .
# → { "error": "Token reuse detected — all sessions revoked" }

# 5. Admin endpoint (Farmer token → 403)
curl -k -s -o /dev/null -w "%{{http_code}}" $BASE/api/admin/users \
  -H "Authorization: Bearer $ACCESS"
# → 403

# 6. Admin login and admin endpoint
ADMIN=$(curl -k -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{{"email":"admin@ugaav.in","password":"Admin@12345"}}' | jq -r '.accessToken')
curl -k -s $BASE/api/admin/users -H "Authorization: Bearer $ADMIN" | jq .
# → [ { "email": "rahul.verma@example.in", ... }, { "email": "admin@ugaav.in", ... } ]
""", "lifecycle.sh", lang="bash")}

<h3>Stretch goals</h3>
{ul(["Add email confirmation: generate token with <code>userManager.GenerateEmailConfirmationTokenAsync</code>, send a link (use a stub IEmailSender), and add a <code>GET /api/auth/confirm-email</code> endpoint.",
"Implement mobile OTP registration (Indian context): store a pending registration with the phone number, generate a 6-digit OTP, verify it in a second step, then create the Identity user.",
"Add a <code>GET /api/admin/refresh-tokens</code> endpoint that lists active tokens per user (useful for a 'sessions' management page).",
"Publish a JWKS endpoint (<code>GET /.well-known/jwks.json</code>) with the public key (switch to RS256) so the Week 19 Blog API can verify tokens without a shared secret."])}
''',
iqs=[("Basic","What does a TokenService do?","It owns JWT creation (CreateAccessToken) and refresh token generation/hashing. Separating it from AuthService keeps the cryptographic concerns in one tested class."),
("Basic","Why is the AuthController thin in this design?","Business logic (Identity calls, token management, chain revocation) lives in UgaavAuthService. The controller only maps HTTP concerns: HTTP verbs, status codes, request/response shapes. This makes the service independently testable."),
("Intermediate","How would you scale this AuthService horizontally to three instances?","JWT validation is stateless (each instance verifies the signature). The bottleneck is the refresh-token DB row. Use a central SQL Server or Redis for refresh tokens. Avoid storing any session state in memory — the service must be stateless between requests."),
("Intermediate","How do you prevent refresh token theft via mobile app transport?","(1) HTTPS only (certificate pinning on the mobile client). (2) HttpOnly Secure cookie for the refresh token (web) or OS-level secure storage (iOS Keychain, Android Keystore). (3) Rotate on every use with reuse detection. (4) Short expiry (7 days). (5) Bind to a device fingerprint claim if the security level justifies the UX cost.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Secure the Week 19 Blog API and Try-to-Break Tests",
"Wire the AuthService JWT into the Week 19 Blog API, add author-or-admin policy, require login for comments, run a systematic try-to-break table, write the README and push to git.",
[("Shared auth config","A common TokenValidationParameters helper referenced by both AuthService and BlogApi — same issuer, audience and key."),
("Author-or-admin policy","A resource-based policy: edit/delete a post only if you are its author (OwnerId == userId) or an Admin."),
("RequireAuthorization for comments","Comments endpoint uses [Authorize] — a valid JWT is required; role is not checked."),
("Try-to-break table","Systematic adversarial testing: expired token, tampered token, privilege escalation, refresh reuse, lockout.")],
["Both services read Jwt:Key, Jwt:Issuer, Jwt:Audience from configuration — identical values required.",
"Resource-based checks in BlogApi use IAuthorizationService.AuthorizeAsync with the Post entity, same as Friday.",
"The comment controller only needs [Authorize] — no role, any authenticated user may comment.",
"Test expired tokens by setting AccessTokenMins to 1 and waiting, or by manually editing exp in the token (signature will fail)."],
f'''
<h3>1. Add JWT auth to Week 19 BlogApi</h3>
{C(r"""
// BlogApi/Program.cs — add the same JWT setup as AuthService
// (copy the AddAuthentication / AddJwtBearer block; share the same appsettings values)

// User-secrets for BlogApi (must match AuthService)
dotnet user-secrets set "Jwt:Key"      "ugaav-auth-service-secret-key-32bytesminimum!"
dotnet user-secrets set "Jwt:Issuer"   "ugaav-auth"
dotnet user-secrets set "Jwt:Audience" "ugaav-api"
""", lang="bash")}
{tip("In production, both services read <code>Jwt:Key</code> from the same Azure Key Vault secret or environment variable — they are never stored in source control.")}

<h3>2. Shared validation helper</h3>
{C(r"""
// Shared/JwtValidation.cs (or a NuGet package / shared project in a monorepo)
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using System.Text;

namespace Shared.Auth;

public static class JwtSetup
{{
    public static void AddJwtAuth(this IServiceCollection services, IConfiguration cfg)
    {{
        var key = cfg["Jwt:Key"] ?? throw new InvalidOperationException("Jwt:Key not configured");
        services.AddAuthentication(opt =>
        {{
            opt.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
            opt.DefaultChallengeScheme    = JwtBearerDefaults.AuthenticationScheme;
        }})
        .AddJwtBearer(opt =>
        {{
            opt.TokenValidationParameters = new TokenValidationParameters
            {{
                ValidateIssuer           = true,
                ValidIssuer              = cfg["Jwt:Issuer"],
                ValidateAudience         = true,
                ValidAudience            = cfg["Jwt:Audience"],
                ValidateLifetime         = true,
                ClockSkew                = TimeSpan.Zero,
                ValidateIssuerSigningKey = true,
                IssuerSigningKey         = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(key))
            }};
        }});
    }}
}}
""", "Shared/JwtSetup.cs")}

<h3>3. Author-or-admin policy in BlogApi</h3>
{C(r"""
// BlogApi/Auth/PostAuthHandler.cs
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Authorization.Infrastructure;
using System.Security.Claims;
using BlogApi.Models;

public class PostAuthHandler : AuthorizationHandler<OperationAuthorizationRequirement, Post>
{{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        OperationAuthorizationRequirement requirement,
        Post post)
    {{
        bool isAdmin  = context.User.IsInRole("Admin");
        string? uid   = context.User.FindFirstValue(ClaimTypes.NameIdentifier);
        bool isAuthor = post.AuthorId == uid;

        if (isAdmin || isAuthor) context.Succeed(requirement);
        return Task.CompletedTask;
    }}
}}
""", "BlogApi/Auth/PostAuthHandler.cs")}
{C(r"""
// BlogApi/Controllers/PostsController.cs (excerpt)
[HttpPut("{{id}}")]
[Authorize]
public async Task<IActionResult> Update(int id, [FromBody] UpdatePostDto dto)
{{
    var post = await db.Posts.FindAsync(id);
    if (post is null) return NotFound();

    var auth = await authService.AuthorizeAsync(User, post, PostOperations.Edit);
    if (!auth.Succeeded) return Forbid();   // 403 — authenticated but not the author/admin

    post.Title   = dto.Title;
    post.Content = dto.Content;
    await db.SaveChangesAsync();
    return Ok(post);
}}
""", "BlogApi/Controllers/PostsController.cs (excerpt)")}

<h3>4. Comments require login</h3>
{C(r"""
// BlogApi/Controllers/CommentsController.cs
[ApiController]
[Route("api/posts/{{postId}}/comments")]
[Authorize]                                // any authenticated user may comment
public class CommentsController(...) : ControllerBase
{{
    [HttpPost]
    public async Task<IActionResult> Add(int postId, [FromBody] AddCommentDto dto)
    {{
        string authorId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        // ... save comment with authorId
    }}

    [HttpDelete("{{id}}")]
    public async Task<IActionResult> Delete(int postId, int id)
    {{
        var comment = await db.Comments.FindAsync(id);
        if (comment is null) return NotFound();

        // Author or Admin
        string? uid     = User.FindFirstValue(ClaimTypes.NameIdentifier);
        bool isAdmin    = User.IsInRole("Admin");
        bool isAuthor   = comment.AuthorId == uid;
        if (!isAdmin && !isAuthor) return Forbid();

        db.Comments.Remove(comment);
        await db.SaveChangesAsync();
        return NoContent();
    }}
}}
""", "BlogApi/Controllers/CommentsController.cs")}

<h3>5. Try-to-break table</h3>
{table(["Attack","Steps","Expected result"],[
["Expired access token","Set AccessTokenMins=1 in secrets; login; wait 65 s; call /api/me","401 — token_expired"],
["Tampered payload","Decode token, change role to Admin in payload, re-encode; call /api/admin/users","401 — invalid_signature (backend hashes header+payload with key; tampered payload gives different hash)"],
["Privilege escalation","Login as Farmer; call DELETE /api/posts/1 (created by Admin)","403 — Forbidden (author check fails, not Admin)"],
["Refresh token reuse","Use refresh token once; use the SAME token again","401 error; all tokens for user revoked"],
["Brute-force lockout","POST /api/auth/login 6 times with wrong password","5th attempt sets LockoutEnd; 6th returns locked error; correct password also returns locked for 10 min"],
["No token at all","Call GET /api/me without Authorization header","401 Unauthorized"],
["Stolen token from another user","Use token issued for user A to call /api/posts (author = user B)","403 Forbidden on edit/delete; GET is public"],
["Expired refresh token","Use DB to set ExpiresAt = now - 1 s; then POST /api/auth/refresh","401 — Refresh token expired"]])}

<h3>6. README template</h3>
{C(r"""
# AuthService — Week 20 Micro-Project

## Overview
Standalone ASP.NET Core 8 Web API providing JWT-based authentication and
authorisation for the Ugaav platform. Issues short-lived access tokens (15 min)
paired with rotated refresh tokens (7 days).

## Endpoints
| Method | Route                      | Auth        | Description                        |
|--------|----------------------------|-------------|------------------------------------|
| POST   | /api/auth/register         | None        | Register; returns token pair       |
| POST   | /api/auth/login            | None        | Login; returns token pair          |
| POST   | /api/auth/refresh          | None        | Rotate refresh token               |
| POST   | /api/auth/logout           | Bearer      | Revoke refresh token               |
| POST   | /api/auth/change-password  | Bearer      | Change password, revoke sessions   |
| GET    | /api/me                    | Bearer      | Current user info                  |
| GET    | /api/admin/users           | Bearer+Admin| List all users                     |

## Setup
```bash
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourStrong@Passw0rd" \
  -p 1433:1433 --name sqlserver -d mcr.microsoft.com/mssql/server:2022-latest
dotnet user-secrets set "Jwt:Key" "<min-32-char-secret>"
dotnet user-secrets set "Seed:AdminPassword" "Admin@12345"
dotnet ef database update
dotnet run
```

## Security notes
- Refresh tokens stored as SHA-256 hashes; plain values never persisted
- Rotation with reuse detection: stolen token triggers full chain revocation
- Lockout: 5 failed attempts → 10-minute lockout
""", "README.md", lang="text")}

<h3>7. Git commands</h3>
{C(r"""
cd AuthService
git init
git add .
git commit -m "Week 20: AuthService — JWT, Identity, refresh token rotation"

# If linking to Week 19 Blog API
cd ../BlogApi
git add .
git commit -m "Week 20: Secure BlogApi — JWT auth, author-or-admin policy, comment auth"
""", lang="bash")}

<h3>Week 20 checklist</h3>
{table(["Topic","Done?"],[
["AuthN vs AuthZ; cookie vs token tradeoffs","☐"],
["JWT structure: header / payload / signature","☐"],
["HS256 vs RS256 — when to use each","☐"],
["XSS vs CSRF — which storage option is affected by which","☐"],
["ASP.NET Core Identity: IdentityDbContext, ApplicationUser, tables","☐"],
["UserManager / SignInManager / RoleManager responsibilities","☐"],
["Password hashing (PBKDF2) — never plain text or MD5","☐"],
["Seeding roles and admin on startup (not in migration)","☐"],
["JsonWebTokenHandler for token creation; JwtBearer for validation","☐"],
["TokenValidationParameters: issuer, audience, lifetime, ClockSkew","☐"],
["user-secrets for Jwt:Key in development","☐"],
["401 (not authenticated) vs 403 (not authorised)","☐"],
["Refresh token rotation + reuse detection","☐"],
["Storing refresh token HASH in DB (not raw value)","☐"],
["Password reset flow (Identity token, single-use, revoke sessions)","☐"],
["Lockout: MaxFailedAccessAttempts, LockoutTimeSpan","☐"],
["Role-based vs policy-based authorisation","☐"],
["Custom IAuthorizationRequirement + AuthorizationHandler","☐"],
["Resource-based auth with IAuthorizationService.AuthorizeAsync","☐"],
["AuthService scaffold, curl lifecycle walkthrough","☐"],
["BlogApi secured: author-or-admin, comment auth","☐"],
["Try-to-break table all rows passing","☐"]])}

<h3>5-question quiz</h3>
<details><summary>Q1. What does this response code mean: a valid JWT is present but the user has role Farmer and the endpoint requires Admin?</summary>
{C(r"""
// Which HTTP status is returned?
// A) 200   B) 401   C) 403   D) 404
""")}<b>C — 403 Forbidden.</b> The request is authenticated (valid JWT) but not authorised (wrong role). 401 means not authenticated at all.</details>

<details><summary>Q2. What prints / what happens?</summary>
{C(r"""
// A refresh token was used once (successfully rotated).
// The same raw token value is presented again to POST /api/auth/refresh.
// What is the expected behaviour?
""")}<b>All active refresh tokens for that user are revoked.</b> The reuse detection path: the token exists in the DB but is already marked RevokedAt (not null). The system interprets a revoked token being presented as a sign of theft and calls RevokeChainAsync for the user, logging them out everywhere.</details>

<details><summary>Q3. Does this compile and run correctly?</summary>
{C(r"""
var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes("short"));
var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
""")}<b>Compiles but throws at runtime.</b> HS256 requires a key of at least 128 bits (16 bytes for the minimum, 256 bits / 32 bytes recommended). The string "short" is 5 bytes → <code>ArgumentOutOfRangeException: IDX10720: ... key size must be greater than 128 bits</code>.</details>

<details><summary>Q4. What is wrong with this token-storage strategy?</summary>
{C(r"""
// In a React SPA:
// 1. POST /api/auth/login  →  store accessToken in localStorage
// 2. Every fetch: Authorization: Bearer localStorage.getItem('accessToken')
""")}<b>XSS vulnerability.</b> Any injected script on the page can call <code>localStorage.getItem('accessToken')</code> and exfiltrate the token to an attacker's server. Prefer an HttpOnly Secure cookie (not readable by JS) or in-memory storage with a silent refresh mechanism.</details>

<details><summary>Q5. AuthorizationHandler — Succeed, Fail or neither?</summary>
{C(r"""
protected override Task HandleRequirementAsync(
    AuthorizationHandlerContext ctx,
    MinAgeRequirement req)
{
    var dob = ctx.User.FindFirstValue("date_of_birth");
    if (dob is null) return Task.CompletedTask;   // ← what happens here?

    if (DateTime.TryParse(dob, out var birth) && DateTime.Today.Year - birth.Year >= req.MinAge)
        ctx.Succeed(req);
    return Task.CompletedTask;
}
""")}<b>Leaving the requirement pending (neither Succeed nor Fail).</b> When <code>dob</code> is null the handler returns without calling Succeed or Fail. Other handlers for this requirement may still succeed it. If no handler succeeds, the requirement fails. This is the correct behaviour — only call <code>ctx.Fail()</code> if you want to explicitly deny access regardless of other handlers.</details>

<div class="note tip"><b>Next week:</b> Week 21 — Background jobs and real-time communication. <code>IHostedService</code>, <code>BackgroundService</code>, Hangfire for recurring jobs, and SignalR for push notifications — plus a report-emailer background service and a live chat feature.</div>
''',
iqs=[("Basic","How do you share the JWT signing key between AuthService and BlogApi without committing it to source control?","In development: dotnet user-secrets on each project, both set to the same value. In production: a shared environment variable (e.g. ASPNETCORE_Jwt__Key) set at deploy time, or a secret manager like Azure Key Vault referenced by both apps."),
("Basic","What is the minimum you must add to Week 19 BlogApi to accept tokens from AuthService?","Add the same AddAuthentication/AddJwtBearer block with matching Jwt:Key, Jwt:Issuer, Jwt:Audience. Call app.UseAuthentication() before app.UseAuthorization(). That's it — no Identity package is needed in the consumer service."),
("Intermediate","A user updates their email. What security steps should follow?","(1) Re-verify the new email (send a confirmation link). (2) Revoke all refresh tokens — the sub claim in existing JWTs still has the old user ID, but the email claim will be stale. (3) If the JWT contains an email claim, force re-login so a fresh token with the new email is issued."),
("Intermediate","How would you implement a 'force logout all devices' feature for an admin?","Revoke all refresh tokens for the user (set RevokedAt on every row for that UserId). Access tokens will expire naturally within their lifetime (15 min). For immediate invalidation, increment a user version counter stored in a fast cache (Redis) and include it as a claim; validate on every request.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","AuthN vs AuthZ, Cookies vs Tokens, JWT Anatomy","JWT Fundamentals","AuthN vs AuthZ, cookie vs token, JWT structure, HMAC vs RSA, storage risks, HTTPS.","2 hrs"),
 (2,"TUE","ASP.NET Core Identity","ASP.NET Identity","IdentityDbContext, ApplicationUser, UserManager, RoleManager, seeding.","2 hrs"),
 (3,"WED","Issuing and Validating JWTs","JWT Issuance","JwtBearer, TokenValidationParameters, JsonWebTokenHandler, 401 vs 403.","2 hrs"),
 (4,"THU","Refresh Tokens and Password Reset","Refresh Tokens","Rotation, reuse detection, token chain, password reset, lockout.","2 hrs"),
 (5,"FRI","Roles, Policies and Resource-Based Checks","Authorisation","Custom requirements, handlers, IAuthorizationService, secure-by-default.","2 hrs"),
 (6,"SAT","AuthService Micro-Project","Project: AuthService","Full service: register, login, refresh, logout, curl lifecycle.","4 hrs"),
 (7,"SUN","Secure Blog API and Try-to-Break","Secure Blog API","BlogApi JWT integration, author-or-admin, adversarial tests, checklist, quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week20.html", 20,
      "Week 20 — Authentication and Authorisation", "Phase 2", "~18 hrs",
      ["Phase 2 · Week 20 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "Auth service"],
      "Security is not a feature you add at the end — it is load-bearing from day one. This week you'll understand how JWT authentication and ASP.NET Core Identity fit together, issue and validate tokens correctly, implement refresh-token rotation with reuse detection, and design authorisation policies from simple role checks to resource-based handlers. The weekend project is a standalone AuthService that you then wire into the Week 19 Blog API.",
      cards, days)
print("built")
