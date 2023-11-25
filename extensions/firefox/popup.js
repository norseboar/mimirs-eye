const TRUE_ASSESSMENT = "true";
const FALSE_ASSESSMENT = "false";
const UNCLEAR_ASSESSMENT = "unclear";
const NOT_FOUND_ASSESSMENT = "notfound";

function showCheckedClaims(claims) {
  const content = document.getElementById("content");

  const header = document.createElement("h2");
  header.textContent = "Claims";

  content.appendChild(header);

  claims.forEach((claim) => {
    const summary = document.createElement("h4");
    summary.textContent = claim.summary;
    content.appendChild(summary);

    const assessment = document.createElement("p");
    assessment.classList.add("assessment");
    assessment.classList.add(`assessment--${claim.overallAssessment}`);
    switch (claim.overallAssessment) {
      case TRUE_ASSESSMENT:
        assessment.textContent = "True";
        break;
      case FALSE_ASSESSMENT:
        assessment.textContent = "False";
        break;
      case UNCLEAR_ASSESSMENT:
        assessment.textContent = "Unclear";
        break;
    }
    content.appendChild(assessment);

    const citations = document.createElement("ul");
    citations.classList.add("citations");
    claim.citations[TRUE_ASSESSMENT].forEach((citation) => {
      const citationItem = document.createElement("li");
      citationItem.innerHTML = `<a href="${citation.link}">${citation.summary}</a>`;
      citations.appendChild(citationItem);
    });
    content.appendChild(citations);
  });
}

let tabURL = "";
(() => {
  browser.tabs
    .query({ active: true, currentWindow: true })
    .then((tabs) => {
      tabURL = tabs[0].url;
      return browser.storage.local.get(tabURL);
    })
    .then((storedData) => {
      console.log("Loaded storedData");
      console.log(storedData);
      if ("claims" in storedData) {
        showCheckedClaims(storedData.claims);
      } else {
        const content = document.getElementById("content");
        const checkButton = document.createElement("button");
        checkButton.textContent = "Fact-check this page";

        checkButton.addEventListener("click", () => {
          fetch("http://localhost:3000/check-article", {
            method: "POST",
            body: JSON.stringify({
              url: tabURL,
            }),
            headers: {
              "Content-Type": "application/json",
            },
          })
            .then((response) => response.json())
            .then((data) => {
              console.log("Received data");
              console.log(data);
              browser.storage.local.set({ [data.url]: data });
              showCheckedClaims(data.claims);
            })
            .catch((error) => {
              console.error("Error:", error);
            });
        });

        content.appendChild(checkButton);
      }
    });
})();
