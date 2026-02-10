import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useJob } from "../state/JobState.jsx";

const DEPARTMENTS = [
  "AIgrow",
  "Battery",
  "Chargnet",
  "Design",
  "Elektrateq",
  "Mechanical",
  "Power Electronics",
  "Product Development",
  "Voltmotive"
];

const PROJECTS = [
  "ATV",
  "Drone",
  "ETX",
  "eVTOL",
  "Fast Charger",
  "Fertigator",
  "Green House",
  "Humiditifier",
  "L2 Charger",
  "Landscaping",
  "Mini Cooper",
  "Street Bike",
  "Small Car",
  "Tuk Charger",
  "UFill",
  "Water Management",
  "Workshop",
  "Vteq"
];

export default function CreateJob() {
  const { state, dispatch } = useJob();
  const nav = useNavigate();

  const [department, setDepartment] = useState("Battery");
  const [project, setProject] = useState("Street Bike");

  useEffect(() => {
    if (state.tabs.length === 0) {
      dispatch({ type: "ADD_TAB" });
    }
  }, []);

  function next() {
    dispatch({ type: "SET_JOB_META", department, project });
    nav("/tabs");
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="text-2xl font-semibold">Create Job</div>
      <div className="text-neutral-400 text-sm mt-1">
        Select department and project
      </div>

      <div className="mt-6 space-y-4 bg-neutral-900 border border-neutral-800 p-6 rounded-2xl">
        <div>
          <div className="text-sm text-neutral-300 mb-2">Department</div>
          <select
            className="w-full rounded-xl bg-neutral-950 border border-neutral-800 px-4 py-3"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          >
            {DEPARTMENTS.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </div>

        <div>
          <div className="text-sm text-neutral-300 mb-2">Project</div>
          <select
            className="w-full rounded-xl bg-neutral-950 border border-neutral-800 px-4 py-3"
            value={project}
            onChange={(e) => setProject(e.target.value)}
          >
            {PROJECTS.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>

        <button
          onClick={next}
          className="w-full rounded-xl bg-white text-black font-medium py-3 hover:opacity-90"
        >
          Next
        </button>
      </div>
    </div>
  );
}
