document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("searchInput");
  const linksList = document.getElementById("links-list");

  searchInput.addEventListener("keyup", function (event) {
    const query = searchInput.value;

    if (query.length < 2) {
      linksList.innerHTML = "";
      return;
    }

    fetch(`/api/recherche?q=${encodeURIComponent(query)}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        linksList.innerHTML = ""; // Vide la liste actuelle
        if (data.length > 0) {
          data.forEach((item) => {
            const listItem = document.createElement("li");
            listItem.className = "link-item";
            listItem.setAttribute("data-category", item.categorie);
            listItem.innerHTML = `
                            <a href="${item.url}" target="_blank">
                                <h3><i class="fas fa-link icon"></i>${item.nom_entite}</h3>
                                <p class="category">${item.categorie}</p>
                            </a>
                        `;
            linksList.appendChild(listItem);
          });
        } else {
          linksList.innerHTML =
            '<li class="no-results">Aucun résultat trouvé pour votre recherche.</li>';
        }
      })
      .catch((error) => {
        console.error("Erreur lors de la recherche:", error);
        linksList.innerHTML =
          '<li class="error">Erreur de connexion. Vérifiez que le serveur est démarré.</li>';
      });
  });
});
