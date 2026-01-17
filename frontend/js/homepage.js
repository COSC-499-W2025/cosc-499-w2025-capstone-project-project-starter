const API_BASE = "http://localhost:5001";

// Upload project
document.getElementById("uploadBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("zipFile");

  if (!fileInput.files.length) {
    alert("Please select a zip file");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const response = await fetch(`${API_BASE}/projects/upload`, {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    document.getElementById("uploadResult").textContent =
      JSON.stringify(data, null, 2);
  } catch (err) {
    console.error(err);
    alert("Upload failed");
  }
});

// Load projects
document.getElementById("loadProjectsBtn").addEventListener("click", async () => {
  try {
    const response = await fetch(`${API_BASE}/projects`);
    const data = await response.json();

    document.getElementById("projectsResult").textContent =
      JSON.stringify(data, null, 2);
  } catch (err) {
    console.error(err);
    alert("Failed to load projects");
  }
});
