import {
  ButtonItem,
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
} from "decky-frontend-lib";
import { VFC, useState, useEffect } from "react";
import { FaKeyboard } from "react-icons/fa";

const Content: VFC<{ serverAPI: ServerAPI }> = ({ serverAPI }) => {
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
    const result = await serverAPI.callPluginMethod("get_server_status", {});
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
    // Tu devras peut-être ajouter une méthode backend pour récupérer l'IP
    return "steamdeck.local"; // Ou l'IP locale
  };

  return (
    <PanelSection title="Remote Keyboard">
      <PanelSectionRow>
        {!running ? (
          <ButtonItem layout="below" onClick={startServer}>
            Start Server
          </ButtonItem>
        ) : (
          <ButtonItem layout="below" onClick={stopServer}>
            Stop Server
          </ButtonItem>
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
