
const express = require("express");
const path = require("path");
const fs = require("fs");
const session = require("express-session");

// Load environment variables
require('dotenv').config();

const app = express();

// Middleware
app.use(express.urlencoded({ extended: false }));
app.use(express.json());

// Basic logging middleware
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// Session setup
app.use(session({
  secret: process.env.SESSION_SECRET || "automationPracticeSecret",
  resave: false,
  saveUninitialized: true,
  cookie: { maxAge: 600000 } // 10 minutes
}));

// ---------- Load Test Data Safely ----------
const testDataPath = path.join(__dirname, "testData.json"); // make sure this file exists
if (!fs.existsSync(testDataPath)) {
  console.error("Error: testData.json file not found at", testDataPath);
  process.exit(1);
}
let testData = JSON.parse(fs.readFileSync(testDataPath, "utf-8"));

// Add roles to users (default: user, admin, guest)
testData = testData.map(u => {
  if (u.username === 'admin') return { ...u, role: 'admin' };
  if (u.username === 'guest') return { ...u, role: 'guest' };
  return { ...u, role: 'user' };
});

// Audit log array (in-memory for demo)
const auditLog = [];

// ---------- HTML Routes ----------

// Serve help, signup, and forgot-password pages
app.get('/help', (req, res) => {
  res.sendFile(path.join(__dirname, 'views', 'help.html'));
});
app.get('/signup', (req, res) => {
  res.sendFile(path.join(__dirname, 'views', 'signup.html'));
});
app.get('/forgot-password', (req, res) => {
  res.sendFile(path.join(__dirname, 'views', 'forgot-password.html'));
});

// Login page
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "views", "login.html"));
});

// Handle login POST
app.post("/login", (req, res) => {
  const { username, password } = req.body;
  const user = testData.find(u => u.username === username && u.password === password);

  // Audit log login attempt
  auditLog.push({
    timestamp: new Date().toISOString(),
    event: 'login_attempt',
    username,
    success: !!user,
    ip: req.ip
  });

  if (user) {
    req.session.user = username;
    req.session.role = user.role;
    req.session.lastActivity = Date.now();
    auditLog.push({
      timestamp: new Date().toISOString(),
      event: 'login_success',
      username,
      role: user.role,
      ip: req.ip
    });
    return res.redirect("/dashboard");
  }

  // Invalid credentials → send back to login with query error
  return res.redirect("/?error=Invalid+username+or+password");
});

// Dashboard page with dynamic username
app.get("/dashboard", (req, res) => {
  // Session expiry: 10 min inactivity
  if (!req.session.user) return res.redirect("/");
  if (req.session.lastActivity && Date.now() - req.session.lastActivity > 600000) {
    auditLog.push({
      timestamp: new Date().toISOString(),
      event: 'session_expired',
      username: req.session.user,
      ip: req.ip
    });
    req.session.destroy(() => {});
    return res.redirect("/?error=Session+expired");
  }
  req.session.lastActivity = Date.now();
  const dashboardPath = path.join(__dirname, "views", "dashboard.html");
  let html = fs.readFileSync(dashboardPath, "utf-8");
  html = html.replace("{{username}}", req.session.user);
  html = html.replace("{{role}}", req.session.role || 'user');
  res.send(html);
});

// Logout
app.get("/logout", (req, res) => {
  auditLog.push({
    timestamp: new Date().toISOString(),
    event: 'logout',
    username: req.session.user,
    ip: req.ip
  });
  req.session.destroy(err => {
    res.redirect("/");
  });
});

// ---------- JSON API Routes ----------

// Return login page info + users for automation
app.get("/api/login", (req, res) => {
  res.json({ page: "login", users: testData.map(u => u.username) });
});

// Return dashboard info if logged in
app.get("/api/dashboard", (req, res) => {
  if (!req.session.user) return res.status(401).json({ error: "unauthorized" });
  res.json({ status: "logged_in", user: req.session.user, role: req.session.role });
});

// Audit log endpoint (for automation)
app.get("/api/auditlog", (req, res) => {
  res.json(auditLog);
});

// Health check endpoint
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", timestamp: Date.now() });
});

// Test data reset endpoint (for automation)
app.post("/api/testdata/reset", (req, res) => {
  try {
    testData = JSON.parse(fs.readFileSync(testDataPath, "utf-8"));
    res.json({ status: "reset", users: testData.map(u => u.username) });
  } catch (err) {
    res.status(500).json({ error: "reset_failed", details: err.message });
  }
});

// ---------- Fixed API 404 handler (avoids PathError) ----------
app.all(/^\/api\/.*/, (req, res) => {
  res.status(404).json({ error: "not_found" });
});

// ---------- Start Server ----------
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
