import { ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#0D1B2A] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold text-[#E8ECF1] text-center mb-2">
          FIRE Retirement Tracker
        </h1>
        <p className="text-[#D4A843] text-center mb-8">Financial Independence, Retire Early</p>
        {children}
      </div>
    </div>
  );
}
