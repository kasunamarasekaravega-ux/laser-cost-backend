import React, { createContext, useContext, useMemo, useReducer } from "react";

const JobCtx = createContext(null);

const initialState = {
  employeeEmail: "",
  department: "",
  project: "",
  tabs: [],
  previewResult: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_EMAIL":
      return { ...state, employeeEmail: action.value };

    case "SET_JOB_META":
      return { ...state, department: action.department, project: action.project };

    case "ADD_TAB":
      return {
        ...state,
        tabs: [
          ...state.tabs,
          {
            id: crypto.randomUUID(),
            material: "Mild Steel",
            thickness: 1.0,
            files: [],
          },
        ],
      };

    case "REMOVE_TAB":
      return { ...state, tabs: state.tabs.filter((t) => t.id !== action.id) };

    case "UPDATE_TAB":
      return {
        ...state,
        tabs: state.tabs.map((t) => (t.id === action.id ? { ...t, ...action.patch } : t)),
      };

    case "ADD_FILES_TO_TAB": {
      const { id, files } = action;
      return {
        ...state,
        tabs: state.tabs.map((t) =>
          t.id === id
            ? {
                ...t,
                files: [
                  ...t.files,
                  ...files.map((f) => ({
                    file: f,
                    qty: 1,
                  })),
                ],
              }
            : t
        ),
      };
    }

    case "UPDATE_FILE_QTY": {
      const { tabId, index, qty } = action;
      return {
        ...state,
        tabs: state.tabs.map((t) =>
          t.id === tabId
            ? {
                ...t,
                files: t.files.map((item, i) => (i === index ? { ...item, qty } : item)),
              }
            : t
        ),
      };
    }

    case "REMOVE_FILE": {
      const { tabId, index } = action;
      return {
        ...state,
        tabs: state.tabs.map((t) =>
          t.id === tabId ? { ...t, files: t.files.filter((_, i) => i !== index) } : t
        ),
      };
    }

    case "SET_PREVIEW":
      return { ...state, previewResult: action.value };

    case "RESET":
      return initialState;

    default:
      return state;
  }
}

export function JobProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <JobCtx.Provider value={value}>{children}</JobCtx.Provider>;
}

export function useJob() {
  const ctx = useContext(JobCtx);
  if (!ctx) throw new Error("useJob must be used inside JobProvider");
  return ctx;
}
