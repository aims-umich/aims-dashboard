document.addEventListener("DOMContentLoaded", function () {
    var articlesByMonth = {};

    fetch("/articles.json")
        .then(response => response.json())
        .then(data => {
            articlesByMonth = data;
        })
        .catch(error => console.error("Error loading articles data:", error));

    window.showArticles = function (month) {
        let articlesTable = document.querySelector(".articles-table");
        articlesTable.innerHTML = "";

        // Create the table header
        let thead = document.createElement("thead");
        thead.innerHTML = `
            <tr>
                <th>Date</th>
                <th>Author</th>
                <th>Article</th>
            </tr>
        `;
        articlesTable.appendChild(thead);

        // Create the table body
        let tbody = document.createElement("tbody");
        
        if (articlesByMonth[month] && articlesByMonth[month].length > 0) {
            articlesByMonth[month].forEach(article => {
                let row = document.createElement("tr");
                row.innerHTML = `
                    <td>${article.date}</td>
                    <td>${article.author}</td>
                    <td>${article.title}</td>
                `;
                tbody.appendChild(row);
            });
        } else {
            let row = document.createElement("tr");
            row.innerHTML = `<td colspan="3" style="text-align:center;">No articles available for this month.</td>`;
            tbody.appendChild(row);
        }
        articlesTable.appendChild(tbody);
    };
});


