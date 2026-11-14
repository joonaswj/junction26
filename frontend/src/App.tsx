import { useState, useEffect } from "react";
import { getMessage } from "./api";

function App() {
    const [message, setMessage] = useState("Connecting...");

    useEffect(() => {
        getMessage()
            .then((data) => {
                console.log("Backend response:", data);
                setMessage(data.message);
            })
            .catch((error) => {
                console.error("API error:", error);
                setMessage("Could not connect to backend");
            });
    }, []);

    return (
        <div style={{ padding: "40px", color: "black" }}>
            <h1>Junction26</h1>
            <h2>{message}</h2>
        </div>
    );
}

export default App;

