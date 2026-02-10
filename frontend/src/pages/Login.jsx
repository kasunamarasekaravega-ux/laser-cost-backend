import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useJob } from "../state/JobState.jsx";

export default function Login() {
  const { dispatch } = useJob();
  const [email, setEmail] = useState("");
  const nav = useNavigate();

  function onLogin(e) {
    e.preventDefault();
    if (!email.trim()) return;
    dispatch({ type: "SET_EMAIL", value: email.trim() });
    nav("/create");
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl bg-neutral-900 border border-neutral-800 p-6 shadow">
        <div className="text-2xl font-semibold">Laser Costing</div>
        <div className="text-neutral-400 mt-1">
          Internal job costing system
        </div>

        <form onSubmit={onLogin} className="mt-6 space-y-3">
          <label className="block text-sm text-neutral-300">
            Employee email
          </label>
          <input
            className="w-full rounded-xl bg-neutral-950 border border-neutral-800 px-4 py-3 outline-none focus:border-neutral-600"
            placeholder="name@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button className="w-full rounded-xl bg-white text-black font-medium py-3 hover:opacity-90">
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}
