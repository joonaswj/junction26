const API_URL = "http://localhost:8000";

export async function getMessage() {
    const response = await fetch(`${API_URL}/`);

    if (!response.ok) {
        throw new Error("API request failed");
    }

    return response.json();
}
