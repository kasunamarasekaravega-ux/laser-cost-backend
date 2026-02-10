import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import CreateJob from "./pages/CreateJob.jsx";
import Tabs from "./pages/Tabs.jsx";
import Review from "./pages/Review.jsx";
import { JobProvider, useJob } from "./state/JobState.jsx";

function GuardedRoute({ children }) {
  const { state } = useJob();
  if (!state.employeeEmail) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <JobProvider>
      <div className="min-h-screen bg-neutral-950 text-neutral-100">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route
            path="/create"
            element={
              <GuardedRoute>
                <CreateJob />
              </GuardedRoute>
            }
          />
          <Route
            path="/tabs"
            element={
              <GuardedRoute>
                <Tabs />
              </GuardedRoute>
            }
          />
          <Route
            path="/review"
            element={
              <GuardedRoute>
                <Review />
              </GuardedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </JobProvider>
  );
}
