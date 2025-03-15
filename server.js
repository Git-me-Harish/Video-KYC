require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const bcrypt = require('bcrypt');
const session = require('express-session');
const path = require('path');
const { exec } = require('child_process');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Session Management
app.use(session({
    secret: process.env.SESSION_SECRET || 'your-secret-key',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false } // Set to true if using HTTPS
}));

// MongoDB Connection
mongoose.connect(process.env.MONGO_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
})
.then(() => console.log('Connected to MongoDB'))
.catch(err => console.error('MongoDB connection error:', err));

// User Schema
const userSchema = new mongoose.Schema({
    fullName: { type: String, required: true },
    email: { type: String, required: true, unique: true },
    password: { type: String, required: true },
});

const User = mongoose.model('User', userSchema);

// Middleware to check if user is authenticated
const isAuthenticated = (req, res, next) => {
    if (req.session.user) {
        next(); // User is authenticated
    } else {
        res.redirect('/login'); // Redirect to login if not authenticated
    }
};

// Proxy requests to the Flask app
app.use('/chat', createProxyMiddleware({ 
    target: 'http://localhost:5000', // Flask app URL
    changeOrigin: true, // Change the origin of the host header to the target URL
    pathRewrite: { '^/chat': '/' }, // Rewrite the path (remove /chat prefix)
}));

// Routes

// Serve Home Page (Protected Route)
app.get('/', isAuthenticated, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Serve Login Page
app.get('/login', (req, res) => {
    if (req.session.user) {
        return res.redirect('/');
    }
    res.sendFile(path.join(__dirname, 'public', 'login.html'));
});

// Serve Registration Page
app.get('/register', (req, res) => {
    if (req.session.user) {
        return res.redirect('/');
    }
    res.sendFile(path.join(__dirname, 'public', 'register.html'));
});

// Registration Endpoint
app.post('/register', async (req, res) => {
    try {
        const { fullName, email, password } = req.body;

        // Check if user already exists
        const existingUser = await User.findOne({ email });
        if (existingUser) {
            return res.status(400).json({ message: 'User already exists' });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Create new user
        const newUser = new User({ fullName, email, password: hashedPassword });
        await newUser.save();

        res.status(201).json({ message: 'Registration successful', redirect: '/login' });
    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
});

// Login Endpoint
app.post('/login', async (req, res) => {
    try {
        const { email, password } = req.body;
        const user = await User.findOne({ email });
        if (!user || !(await bcrypt.compare(password, user.password))) {
            return res.status(400).json({ message: 'Invalid email or password' });
        }
        req.session.user = { id: user._id, email: user.email };
        req.session.save();
        res.status(200).json({ message: 'Login successful', redirect: '/' });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
});

// Logout Endpoint
app.post('/logout', (req, res) => {
    req.session.destroy((err) => {
        if (err) {
            return res.status(500).json({ message: 'Logout failed' });
        }
        res.clearCookie('connect.sid');
        res.status(200).json({ message: 'Logout successful', redirect: '/login' });
    });
});

// Route to Launch PyQt5 KYC Verification App
app.get('/launch-kyc', (req, res) => {
    const pythonScriptPath = path.join(__dirname, 'path_to_your_pyqt5_script.py');

    exec(`python ${pythonScriptPath}`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error launching PyQt5: ${error.message}`);
            return res.status(500).send('Failed to launch KYC verification.');
        }
        if (stderr) {
            console.error(`PyQt5 Error: ${stderr}`);
            return res.status(500).send('PyQt5 encountered an error.');
        }
        console.log(`PyQt5 Output: ${stdout}`);
        res.send('KYC Verification App Launched');
    });
});

// Start Server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});