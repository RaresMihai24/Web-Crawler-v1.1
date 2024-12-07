document.getElementById('crawl-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(e.target);

    fetch('/crawl', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const treeContainer = document.getElementById('tree-container');
        treeContainer.innerHTML = '';
        const tree = createTreeView(data);
        treeContainer.appendChild(tree);
    });
});

document.getElementById('stop-crawl').addEventListener('click', function() {
    fetch('/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        alert('Crawling stopped.');
    });
});

function createTreeView(data) {
    const ul = document.createElement('ul');
    const li = document.createElement('li');

    const span = document.createElement('span');
    span.classList.add('node-label');
    span.textContent = data.name;

    li.appendChild(span);

    if (data.children && data.children.length > 0) {
        span.classList.add('expandable');

        const nestedUl = document.createElement('ul');
        nestedUl.classList.add('nested', 'hidden');
        data.children.forEach(child => {
            nestedUl.appendChild(createTreeView(child));
        });
        li.appendChild(nestedUl);

        span.addEventListener('click', function(e) {
            e.stopPropagation();
            nestedUl.classList.toggle('hidden');
            nestedUl.classList.toggle('active');
            span.classList.toggle('expanded');
        });
    }

    ul.appendChild(li);
    return ul;
}