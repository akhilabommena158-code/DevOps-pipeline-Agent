const $ = (id) => document.getElementById(id);

$("analyzeBtn").addEventListener("click", async () => {
    $("error").classList.add("hidden");
    const path = $("project_path").value.trim();

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({project_path: path})
        });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || "Analysis failed");

        const a = data.analysis;
        $("facts").innerHTML = `
            <div class="fact"><strong>Language</strong>${a.language}</div>
            <div class="fact"><strong>Framework</strong>${a.framework}</div>
            <div class="fact"><strong>Dependencies</strong>${a.dependency_file}</div>
            <div class="fact"><strong>Package manager</strong>${a.package_manager}</div>
            <div class="fact"><strong>Tests</strong>${a.tests_detected ? "Detected" : "Not detected"}</div>
            <div class="fact"><strong>Docker</strong>${a.docker_detected ? "Detected" : "Not detected"}</div>
            <div class="fact"><strong>Files scanned</strong>${a.file_count}</div>
        `;

        $("recommendations").innerHTML = "";
        a.recommendations.forEach(r => {
            const li = document.createElement("li");
            li.textContent = r;
            $("recommendations").appendChild(li);
        });

        $("files").textContent = a.sample_files.join("\n");
        $("analysisCard").classList.remove("hidden");

        // Use detected values to pre-fill pipeline generation.
        const langMap = {
            "Python": "python",
            "JavaScript / Node.js": "node",
            "JavaScript / TypeScript": "javascript",
            "Java": "java"
        };
        if (langMap[a.language]) $("language").value = langMap[a.language];
        $("test_command").value = a.recommended_test_command;
        $("build_command").value = a.recommended_build_command;
    } catch (e) {
        $("error").textContent = e.message;
        $("error").classList.remove("hidden");
    }
});

$("pipelineForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("error").classList.add("hidden");

    const payload = {
        project_name: $("project_name").value,
        language: $("language").value,
        test_command: $("test_command").value,
        build_command: $("build_command").value,
        deploy_target: $("deploy_target").value
    };

    try {
        const response = await fetch("/api/generate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || "Pipeline generation failed");

        $("workflow").textContent = data.workflow;
        $("result").classList.remove("hidden");
    } catch (e) {
        $("error").textContent = e.message;
        $("error").classList.remove("hidden");
    }
});

$("copyBtn").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("workflow").textContent);
    $("copyBtn").textContent = "Copied!";
    setTimeout(() => $("copyBtn").textContent = "Copy YAML", 1200);
});
