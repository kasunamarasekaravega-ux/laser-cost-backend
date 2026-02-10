import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../config.js";
import { useJob } from "../state/JobState.jsx";

export default function Review() {
  const { state, dispatch } = useJob();
  const nav = useNavigate();

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);

  const preview = state.previewResult;

  if (!preview) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-6">
          <div className="text-lg font-semibold">No preview found</div>
          <div className="text-neutral-400 mt-1">Go back and calculate first.</div>
          <button
            onClick={() => nav("/tabs")}
            className="mt-4 rounded-xl bg-white text-black font-medium px-6 py-3 hover:opacity-90"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  async function submit() {
    setErr("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(preview),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }

      const data = await res.json();
      setResult(data);
    } catch (e) {
      setErr(`Submit failed: ${String(e.message || e)}`);
    } finally {
      setLoading(false);
    }
  }

  function newJob() {
    dispatch({ type: "RESET" });
    nav("/");
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-2xl font-semibold">Review</div>
          <div className="text-neutral-400 text-sm mt-1">
            Confirm costs and submit job
          </div>
        </div>
        <button
          onClick={() => nav("/tabs")}
          className="rounded-xl bg-neutral-900 border border-neutral-800 px-4 py-2 hover:border-neutral-700"
        >
          Back
        </button>
      </div>

      {err && (
        <div className="mt-4 rounded-xl border border-red-800 bg-red-950/30 p-3 text-sm text-red-200">
          {err}
        </div>
      )}

      <div className="mt-6 rounded-2xl bg-neutral-900 border border-neutral-800 p-6">
        <div className="text-sm text-neutral-400">
          {preview.department} • {preview.project} • {preview.employee_email}
        </div>

        <div className="mt-4 space-y-3">
          {preview.tabs.map((t, idx) => (
            <div key={idx} className="rounded-xl bg-neutral-950 border border-neutral-800 p-4">
              <div className="flex items-center justify-between">
                <div className="font-medium">{t.material}</div>
                <div className="text-sm text-neutral-300">{t.cost_text}</div>
              </div>
              <div className="mt-2 text-xs text-neutral-500">
                Thickness: {t.thickness_sheet} • Gas: {t.gas} • Qty: {t.quantity} • Cut:{" "}
                {t.total_cut_len_mm} mm • Area: {t.total_area_sqft} sqft
              </div>
              <div className="mt-2 text-xs text-neutral-500 truncate">
                Drive: {t.drive_folder_url}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-5 flex items-center justify-between">
          <div className="text-neutral-300">Grand Total</div>
          <div className="text-xl font-semibold">
            LKR {Number(preview.grand_total).toLocaleString()}
          </div>
        </div>

        {!result ? (
          <button
            disabled={loading}
            onClick={submit}
            className="mt-5 w-full rounded-xl bg-white text-black font-medium py-3 hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Submitting..." : "Submit Job"}
          </button>
        ) : (
          <div className="mt-5 rounded-xl border border-green-800 bg-green-950/30 p-4">
            <div className="font-semibold text-green-200">Submitted ✅</div>
            <div className="text-sm text-green-200 mt-1">
              Job ID: <span className="font-mono">{result.job_id}</span>
            </div>
            <button
              onClick={newJob}
              className="mt-4 rounded-xl bg-white text-black font-medium px-6 py-2 hover:opacity-90"
            >
              New Job
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
