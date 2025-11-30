const curr_infoSpan = document.querySelector(".curr-info");

document.getElementById("media_type").addEventListener("change", (e) => {
    const resolutionSelect = document.getElementById("resolution");
    const fpsSelect = document.getElementById("fps");
    const abrSelect = document.getElementById("abr");

    const resolutionDiv = document.querySelector(".resolution");
    const fpsDiv = document.querySelector(".fps");
    const abrDiv = document.querySelector(".abr");

    const url = document.getElementById("url").value || "";
    const _type = e.target.value.toLowerCase().trim();

    resolutionSelect.innerHTML = `<option value="best">Best</option>`;
    fpsSelect.innerHTML = `<option value="best">Best</option>`;
    abrSelect.innerHTML = `<option value="best">Best</option>`;

    // 先處理 select 的顯示
    if (_type === "video") {
        resolutionDiv.classList.remove("hidden");
        fpsDiv.classList.remove("hidden");
        abrDiv.classList.add("hidden");
    } else if (_type === "audio") {
        resolutionDiv.classList.add("hidden");
        fpsDiv.classList.add("hidden");
        abrDiv.classList.remove("hidden");
    } else if (_type === "video and audio") {
        resolutionDiv.classList.remove("hidden");
        fpsDiv.classList.remove("hidden");
        abrDiv.classList.remove("hidden");
    }

    curr_infoSpan.textContent = "Fetching qualities...";

    fetch('/qualities', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        })
        .then(response => {
            if (!response.ok) {
                curr_infoSpan.textContent = `Did you type the URL correctly? Server returned: ${response.status}`;
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            let qualities = data;
            console.log(qualities)
            if (!qualities) return;

            if (_type === "video") {
                let resolution = qualities.resolution;
                let fps = qualities.fps;

                resolution.forEach(r => {
                    resolutionSelect.innerHTML += `<option value="${r}">${capitalizeFirst(r)}</option>`;
                });

                fps.forEach(f => {
                    fpsSelect.innerHTML += `<option value="${f}">${capitalizeFirst(f)}</option>`;
                })
            } else if (_type === "audio") {
                let abr = qualities.abr;

                abr.forEach(a => {
                    abrSelect.innerHTML += `<option value="${a}">${capitalizeFirst(a)}</option>`;
                })
            } else if (_type === "video and audio") {
                let resolution = qualities.resolution;
                let fps = qualities.fps;
                let abr = qualities.abr;

                console.log(qualities)

                resolution.forEach(r => {
                    resolutionSelect.innerHTML += `<option value="${r}">${capitalizeFirst(r)}</option>`;
                });

                fps.forEach(f => {
                    fpsSelect.innerHTML += `<option value="${f}">${capitalizeFirst(f)}</option>`;
                });

                abr.forEach(a => {
                    abrSelect.innerHTML += `<option value="${a}">${capitalizeFirst(a)}</option>`;
                });
            }

            curr_infoSpan.textContent = "Fetched qualities.";
        });
});

function capitalizeFirst(str) {
    // 讓第一個字大寫
    str = String(str || "");
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function startDownload() {
    const url = document.getElementById("url").value;
    const type = document.getElementById("media_type").value;

    const resolution = document.getElementById("resolution").value;
    const fps = document.getElementById("fps").value;
    const abr = document.getElementById("abr").value;

    if (!url) {
        curr_infoSpan.textContent = 'Invaild URL haha';
        alert("Please enter a valid YouTube URL.");
        return;
    }

    curr_infoSpan.textContent = 'Downloading...';

    document.getElementById("download-btn").disabled = true;
    try {
        fetch('/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, type, resolution, fps, abr })
            })
            .then(response => {
                if (!response.ok) {
                    document.getElementById("download-btn").disabled = false;
                    curr_infoSpan.textContent = `Download failed: ${response.status}`;
                    throw new Error(`Download failed: ${response.status}`);
                }

                const disposition = response.headers.get("Content-Disposition");
                let filename = "downloaded_file";

                if (disposition) {
                    // 嘗試解析 filename*=utf-8''xxx
                    const match = disposition.match(/filename\*=utf-8''(.+)/);
                    if (match && match[1]) {
                        filename = decodeURIComponent(match[1]); // 轉回中文
                    } else {
                        // 備用：解析 filename="xxx"
                        const match2 = disposition.match(/filename="(.+)"/);
                        if (match2 && match2[1]) {
                            filename = match2[1];
                        }
                    }
                }

                return response.blob().then(blob => ({ blob, filename }));
            })
            .then(({ blob, filename }) => {
                const downloadUrl = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = filename; // 使用解析後的檔名
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(downloadUrl);
                curr_infoSpan.textContent = `Yeahhhh we got a ${type}!!`;
            });
    } catch (error) {
        console.error(error.message);
    } finally {
        document.getElementById("download-btn").disabled = false;
    }
}