import {
  ButtonItem,
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
} from "decky-frontend-lib";
import { FC, useState, useEffect } from "react";
import { FaKeyboard } from "react-icons/fa";

interface ContentProps {
  serverAPI: ServerAPI;
}

interface ServerStatus {
  running: boolean;
  code: string | null;
  clients: number;
}

const Content: FC<ContentProps> = ({ serverAPI }) => {
  const [running, setRunning] = useState(false);
  const [code, setCode] = useState("");
  const [clients, setClients] = useState(0);
  const [port] = useState(8765);

  useEffect(() => {
    updateStatus();
    const interval = setInterval(updateStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const updateStatus = async () => {
    const result = await serverAPI.callPluginMethod<{}, ServerStatus>("get_server_status", {});
    if (result.success) {
      setRunning(result.result.running);
      setCode(result.result.code || "");
      setClients(result.result.clients || 0);
    }
  };

  const startServer = async () => {
    const result = await serverAPI.callPluginMethod("start_server", { port });
    if (result.success) {
      updateStatus();
    }
  };

  const stopServer = async () => {
    await serverAPI.callPluginMethod("stop_server", {});
    updateStatus();
  };

  const getLocalIP = () => {
    return "steamdeck.local";
  };

  return (
    <PanelSection title="Remote Keyboard">
      <PanelSectionRow>
        {!running ? (
          <ButtonItem layout="below" onClick={startServer} label="Start Server" />
        ) : (
          <ButtonItem layout="below" onClick={stopServer} label="Stop Server" />
        )}
      </PanelSectionRow>

      {running && (
        <>
          <PanelSectionRow>
            <div style={{ fontSize: "14px" }}>
              <strong>URL:</strong> http://{getLocalIP()}:{port}
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
};

export default definePlugin((serverApi: ServerAPI) => {
  return {
    title: <div className={staticClasses.Title}>Remote Keyboard</div>,
    content: <Content serverAPI={serverApi} />,
    icon: <FaKeyboard />,
  };
});