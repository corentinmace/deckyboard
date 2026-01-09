import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses
} from "@decky/ui";
import {
  callable,
  definePlugin,
} from "@decky/api";
import { useState, useEffect } from "react";
import { FaKeyboard } from "react-icons/fa";

interface ServerStatus {
  running: boolean;
  code: string | null;
  clients: number;
}

const startServer = callable<[port: number], { success: boolean; code?: string; port?: number }>("start_server");
const stopServer = callable<[], { success: boolean }>("stop_server");
const getServerStatus = callable<[], ServerStatus>("get_server_status");

function Content() {
  const [running, setRunning] = useState(false);
  const [code, setCode] = useState("");
  const [clients, setClients] = useState(0);
  const [port] = useState(8765);

  const updateStatus = async () => {
    try {
      const status = await getServerStatus();
      setRunning(status.running);
      setCode(status.code || "");
      setClients(status.clients || 0);
    } catch (error) {
      console.error("Error fetching status:", error);
    }
  };

  useEffect(() => {
    updateStatus();
    const interval = setInterval(updateStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleStartServer = async () => {
    try {
      const result = await startServer(port);
      if (result.success) {
        updateStatus();
      }
    } catch (error) {
      console.error("Error starting server:", error);
    }
  };

  const handleStopServer = async () => {
    try {
      await stopServer();
      updateStatus();
    } catch (error) {
      console.error("Error stopping server:", error);
    }
  };

  return (
    <PanelSection title="Remote Keyboard">
      <PanelSectionRow>
        {!running ? (
          <ButtonItem
            layout="below"
            onClick={handleStartServer}
          >
            Start Server
          </ButtonItem>
        ) : (
          <ButtonItem
            layout="below"
            onClick={handleStopServer}
          >
            Stop Server
          </ButtonItem>
        )}
      </PanelSectionRow>

      {running && (
        <>
          <PanelSectionRow>
            <div style={{ fontSize: "14px" }}>
              <strong>URL:</strong> http://steamdeck.local:{port}
            </div>
          </PanelSectionRow>
          <PanelSectionRow>
            <div style={{ fontSize: "20px", fontWeight: "bold", textAlign: "center" }}>
              Code: {code}
            </div>
          </PanelSectionRow>
          <PanelSectionRow>
            <div style={{ fontSize: "12px", color: "#aaa" }}>
              Connected clients: {clients}
            </div>
          </PanelSectionRow>
        </>
      )}
    </PanelSection>
  );
}

export default definePlugin(() => {
  console.log("Deckyboard initializing");

  return {
    name: "Deckyboard",
    titleView: <div className={staticClasses.Title}>Remote Keyboard</div>,
    content: <Content />,
    icon: <FaKeyboard />,
    onDismount() {
      console.log("Deckyboard unloading");
    },
  };
});