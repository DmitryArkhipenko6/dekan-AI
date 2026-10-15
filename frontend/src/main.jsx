import React from "react";
import ReactDOM from "react-dom/client";
import {
  CssBaseline,
  ThemeProvider,
  createTheme,
} from "@mui/material";
import App from "./App.jsx";

const theme = createTheme({
  palette: {
    primary: { main: "#14545b", dark: "#103e44", light: "#e6f1ef" },
    secondary: { main: "#d97824" },
    background: { default: "#f4f7f6", paper: "#ffffff" },
    text: { primary: "#1d3033", secondary: "#607477" },
    success: { main: "#23845b" },
    warning: { main: "#a65d0a" },
    error: { main: "#bd3e3e" },
  },
  shape: { borderRadius: 14 },
  typography: {
    fontFamily: '"Roboto", "Arial", sans-serif',
    h4: { fontWeight: 700, letterSpacing: "-0.03em" },
    h5: { fontWeight: 700 },
    button: { textTransform: "none", fontWeight: 700 },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 10, padding: "10px 18px" },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid #e2e9e7",
          boxShadow: "0 8px 28px rgba(21, 63, 68, 0.06)",
        },
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
);
