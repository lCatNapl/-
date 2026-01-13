function loadSubcategories(catId) {
    fetch(`/api/category/1/${catId}`)  // game_id=1 для примера
        .then(r => r.json())
        .then(data => {
            document.getElementById('subcategories').innerHTML = `
                <h2>${data.category[0]}</h2>
                <p>${data.category[1]}</p>
                <div class="subcat-grid">
                    ${data.subcategories.map(cat => 
                        `<div class="category-card">${cat[1]}</div>`
                    ).join('')}
                </div>
            `;
        });
}

function searchGames() {
    const query = document.getElementById('search').value;
    // Поиск по играм и категориям
}
