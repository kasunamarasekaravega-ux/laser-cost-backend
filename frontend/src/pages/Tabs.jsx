import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../config.js";
import { useJob } from "../state/JobState.jsx";

const MATERIALS = [
  "Aluminium",
  "Copper",
  "Mild Steel",
  "Silicon steel",
  "Stainless Steel (SS)",
  "Zinc-Coated Steel",
];

const THICKNESSES = [
  0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0,
];

export default function Tabs() {
  const { state, dispatch } = useJob();
  const nav = useNavigate();

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const canCalculate = useMemo(() => {
    if (!state.department || !state.project) return false;
    if (!state.employeeEmail) return false;
    if (state.tabs.length === 0) return false;
    return state.tabs.every(
      (t) =>
        t.material &&
        t.thickness > 0 &&
        t.files.length > 0 &&
        t.files.every((f) => f.qty > 0)
    );
  }, [state]);

  function addTab() {
    dispatch({ type: "ADD_TAB" });
  }

  async function calculatePreview() {
    setErr("");
    if (!canCalculate) {
      setErr("Please complete all tabs (material, thickness, upload files, qty).");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        employee_email: state.employeeEmail,
        department: state.department,
        project: state.project,
        tabs: state.tabs.map((t) => ({
          material: t.material,
          thickness: t.thickness,
          files: t.files.map((it) => ({
            filename: it.file.name,
            qty: it.qty,
          })),
        })),
      };

      const form = new FormData();
      form.append("payload_json", JSON.stringify(payload));

      // append all files to same "files" field
      state.tabs.forEach((t) => {
        t.files.forEach((it) => {
          form.append("files", it.file, it.file.name);
        });
      });

      const res = await fetch(`${API_BASE}/preview`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }

      const data = await res.json();
      dispatch({ type: "SET_PREVIEW", value: data });
      nav("/review");
    } catch (e) {
      setErr(`Preview failed: ${String(e.message || e)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-2xl font-semibold">Tabs</div>
          <div className="text-neutral-400 text-sm mt-1">
            Each tab = one Material + Thickness group
          </div>
          <div className="text-neutral-500 text-xs mt-1">
            {state.department} • {state.project}
          </div>
        </div>

        <button
          onClick={addTab}
          className="rounded-xl bg-neutral-900 border border-neutral-800 px-4 py-2 hover:border-neutral-700"
        >
          + Add Tab
        </button>
      </div>

      {err && (
        <div className="mt-4 rounded-xl border border-red-800 bg-red-950/30 p-3 text-sm text-red-200">
          {err}
        </div>
      )}

      <div className="mt-6 space-y-4">
        {state.tabs.map((tab) => (
          <TabCard key={tab.id} tab={tab} />
        ))}
      </div>

      <div className="mt-6 flex items-center justify-end gap-3">
        <button
          disabled={loading}
          onClick={() => nav("/create")}
          className="rounded-xl bg-neutral-900 border border-neutral-800 px-4 py-3 hover:border-neutral-700 disabled:opacity-50"
        >
          Back
        </button>

        <button
          disabled={loading || !canCalculate}
          onClick={calculatePreview}
          className="rounded-xl bg-white text-black font-medium px-6 py-3 hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Calculating..." : "Next (Calculate)"}
        </button>
      </div>
    </div>
  );

  function TabCard({ tab }) {
    const { dispatch } = useJob();

    function removeTab() {
      dispatch({ type: "REMOVE_TAB", id: tab.id });
    }

    function onFilesChosen(e) {
      const files = Array.from(e.target.files || []);
      if (files.length === 0) return;
      dispatch({ type: "ADD_FILES_TO_TAB", id: tab.id, files });
      e.target.value = "";
    }

    return (
      <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="text-lg font-semibold">Tab</div>
          <button onClick={removeTab} className="text-sm text-neutral-400 hover:text-neutral-200">
            Remove
          </button>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-neutral-300 mb-2">Material</div>
            <select
              className="w-full rounded-xl bg-neutral-950 border border-neutral-800 px-4 py-3"
              value={tab.material}
              onChange={(e) =>
                dispatch({ type: "UPDATE_TAB", id: tab.id, patch: { material: e.target.value } })
              }
            >
              {MATERIALS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div className="text-sm text-neutral-300 mb-2">Thickness (mm)</div>
            <select
              className="w-full rounded-xl bg-neutral-950 border border-neutral-800 px-4 py-3"
              value={tab.thickness}
              onChange={(e) =>
                dispatch({
                  type: "UPDATE_TAB",
                  id: tab.id,
                  patch: { thickness: Number(e.target.value) },
                })
              }
            >
              {THICKNESSES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4">
          <div className="text-sm text-neutral-300 mb-2">DXF files</div>
          <input
            type="file"
            accept=".dxf,.DXF"
            multiple
            onChange={onFilesChosen}
            className="block w-full text-sm text-neutral-300 file:mr-3 file:rounded-lg file:border-0 file:bg-neutral-800 file:px-4 file:py-2 file:text-neutral-100 hover:file:bg-neutral-700"
          />
        </div>

        <div className="mt-4 space-y-2">
          {tab.files.length === 0 ? (
            <div className="text-sm text-neutral-500">No files added.</div>
          ) : (
            tab.files.map((it, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between gap-3 rounded-xl bg-neutral-950 border border-neutral-800 p-3"
              >
                <div className="truncate text-sm">{it.file.name}</div>

                <div className="flex items-center gap-2">
                  <div className="text-xs text-neutral-400">Qty</div>
                  <input
                    type="number"
                    min="1"
                    value={it.qty}
                    onChange={(e) =>
                      dispatch({
                        type: "UPDATE_FILE_QTY",
                        tabId: tab.id,
                        index: idx,
                        qty: Number(e.target.value),
                      })
                    }
                    className="w-20 rounded-lg bg-neutral-900 border border-neutral-800 px-2 py-1 text-sm"
                  />
                  <button
                    onClick={() => dispatch({ type: "REMOVE_FILE", tabId: tab.id, index: idx })}
                    className="text-xs text-neutral-400 hover:text-neutral-200"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }
}
