import { useState, type FormEvent } from "react";
import { useAuth } from "../contexts/AuthContext";
import { AuthLayout } from "../layouts/AuthLayout";

type Tab = "otp" | "password" | "signup";

export function Login() {
  const [activeTab, setActiveTab] = useState<Tab>("otp");

  return (
    <AuthLayout>
      <div className="bg-[#132E3D] rounded-xl shadow-2xl p-6">
        {/* Tab Navigation */}
        <div className="flex border-b border-[#1A3A5C] mb-6">
          <TabButton active={activeTab === "otp"} onClick={() => setActiveTab("otp")}>
            Email OTP
          </TabButton>
          <TabButton active={activeTab === "password"} onClick={() => setActiveTab("password")}>
            Password
          </TabButton>
          <TabButton active={activeTab === "signup"} onClick={() => setActiveTab("signup")}>
            Sign Up
          </TabButton>
        </div>

        {activeTab === "otp" && <OtpForm />}
        {activeTab === "password" && <PasswordForm />}
        {activeTab === "signup" && <SignupForm />}
      </div>
    </AuthLayout>
  );
}

/* ------------------------------------------------------------------ */
/* Tab Button                                                          */
/* ------------------------------------------------------------------ */

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 pb-3 text-sm font-medium transition-colors cursor-pointer ${
        active
          ? "text-[#D4A843] border-b-2 border-[#D4A843]"
          : "text-[#E8ECF1]/50 hover:text-[#E8ECF1]/80"
      }`}
    >
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* OTP Form                                                            */
/* ------------------------------------------------------------------ */

function OtpForm() {
  const { sendOtp, verifyOtp } = useAuth();
  const [email, setEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const handleSendOtp = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      await sendOtp(email);
      setOtpSent(true);
      setMessage("OTP sent! Check your email.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      await verifyOtp(email, otpCode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid OTP");
    } finally {
      setLoading(false);
    }
  };

  if (!otpSent) {
    return (
      <form onSubmit={handleSendOtp} className="space-y-4">
        <InputField
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="you@example.com"
          required
        />
        <ErrorMessage message={error} />
        <SuccessMessage message={message} />
        <SubmitButton loading={loading}>Send OTP</SubmitButton>
      </form>
    );
  }

  return (
    <form onSubmit={handleVerifyOtp} className="space-y-4">
      <p className="text-sm text-[#E8ECF1]/70">
        OTP sent to <span className="text-[#D4A843]">{email}</span>
      </p>
      <InputField
        label="OTP Code"
        type="text"
        value={otpCode}
        onChange={setOtpCode}
        placeholder="Enter 8-character code"
        maxLength={8}
        required
      />
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />
      <SubmitButton loading={loading}>Verify OTP</SubmitButton>
      <button
        type="button"
        onClick={() => {
          setOtpSent(false);
          setOtpCode("");
          setError("");
          setMessage("");
        }}
        className="w-full text-sm text-[#E8ECF1]/50 hover:text-[#E8ECF1]/80 transition-colors cursor-pointer"
      >
        Back to email
      </button>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/* Password Form                                                       */
/* ------------------------------------------------------------------ */

function PasswordForm() {
  const { loginWithPassword, resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resetSent, setResetSent] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setResetSent(false);
    // Read directly from form elements as fallback for Chrome autofill
    const form = e.target as HTMLFormElement;
    const formEmail = (form.elements.namedItem("email") as HTMLInputElement)?.value || email;
    const formPassword = (form.elements.namedItem("password") as HTMLInputElement)?.value || password;

    if (!formEmail || !formPassword) {
      setError("Please enter both email and password");
      return;
    }

    setLoading(true);
    try {
      await loginWithPassword(formEmail, formPassword);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async () => {
    setError("");
    setResetSent(false);
    if (!email) {
      setError("Enter your email address first, then click Forgot Password");
      return;
    }
    if (resetSent) return; // Prevent spamming while cooldown is active
    setLoading(true);
    try {
      await resetPassword(email);
      setResetSent(true);
      // Auto-clear the success message after 60s cooldown
      setTimeout(() => setResetSent(false), 60000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reset email");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <InputField
        label="Email"
        type="email"
        value={email}
        onChange={setEmail}
        placeholder="you@example.com"
        required
      />
      <InputField
        label="Password"
        type="password"
        value={password}
        onChange={setPassword}
        placeholder="Your password"
        required
      />
      <ErrorMessage message={error} />
      {resetSent && (
        <p className="text-sm text-[#2E8B57] bg-[#2E8B57]/10 border border-[#2E8B57]/20 rounded-lg px-3 py-2">
          Password reset link sent! Check your email.
        </p>
      )}
      <SubmitButton loading={loading}>Log In</SubmitButton>
      <button
        type="button"
        onClick={handleForgotPassword}
        disabled={loading || resetSent}
        className="w-full text-sm text-[#D4A843] hover:text-[#D4A843]/80 transition-colors cursor-pointer disabled:opacity-50"
      >
        {resetSent ? "Reset link sent (wait 60s)" : "Forgot Password?"}
      </button>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/* Signup Form                                                         */
/* ------------------------------------------------------------------ */

function SignupForm() {
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);
    try {
      await signup(email, password);
      setMessage("Account created! Check your email for a confirmation link.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <InputField
        label="Email"
        type="email"
        value={email}
        onChange={setEmail}
        placeholder="you@example.com"
        required
      />
      <InputField
        label="Password"
        type="password"
        value={password}
        onChange={setPassword}
        placeholder="Min 6 characters"
        required
      />
      <InputField
        label="Confirm Password"
        type="password"
        value={confirm}
        onChange={setConfirm}
        placeholder="Re-enter password"
        required
      />
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />
      <SubmitButton loading={loading}>Create Account</SubmitButton>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/* Shared Components                                                   */
/* ------------------------------------------------------------------ */

function InputField({
  label,
  type,
  value,
  onChange,
  placeholder,
  required,
  maxLength,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  maxLength?: number;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-[#E8ECF1]/80 mb-1">{label}</label>
      <input
        name={type === "email" ? "email" : type === "password" ? "password" : label.toLowerCase()}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onInput={(e) => onChange((e.target as HTMLInputElement).value)}
        placeholder={placeholder}
        required={required}
        maxLength={maxLength}
        autoComplete={type === "email" ? "email" : type === "password" ? "current-password" : "off"}
        className="w-full px-4 py-2.5 bg-[#0D1B2A] border border-[#1A3A5C] rounded-lg text-[#E8ECF1] placeholder-[#E8ECF1]/30 focus:outline-none focus:border-[#D4A843] focus:ring-1 focus:ring-[#D4A843] transition-colors"
      />
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  if (!message) return null;
  return (
    <p className="text-sm text-[#E5A100] bg-[#E5A100]/10 border border-[#E5A100]/20 rounded-lg px-3 py-2">
      {message}
    </p>
  );
}

function SuccessMessage({ message }: { message: string }) {
  if (!message) return null;
  return (
    <p className="text-sm text-[#2E8B57] bg-[#2E8B57]/10 border border-[#2E8B57]/20 rounded-lg px-3 py-2">
      {message}
    </p>
  );
}

function SubmitButton({ loading, children }: { loading: boolean; children: React.ReactNode }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full py-2.5 px-4 bg-[#00895E] hover:bg-[#00895E]/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors cursor-pointer"
    >
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Please wait...
        </span>
      ) : (
        children
      )}
    </button>
  );
}

export default Login;
