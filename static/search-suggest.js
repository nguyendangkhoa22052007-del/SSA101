// static/search-suggest.js
(() => {
  const input = document.getElementById('search-input');
  const list = document.getElementById('suggest-list');
  let activeIndex = -1;
  let suggestions = [];

  function debounce(fn, wait=220) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  }

  async function fetchSuggestions(q) {
    if (!q) return updateList([]);
    try {
      const res = await fetch(`/suggest?q=${encodeURIComponent(q)}`);
      if (!res.ok) return updateList([]);
      const data = await res.json();
      updateList(data);
    } catch (e) {
      updateList([]);
    }
  }

  function updateList(items) {
    suggestions = items;
    activeIndex = -1;
    list.innerHTML = '';
    if (!items.length) {
      list.style.display = 'none';
      return;
    }
    list.style.display = 'block';
    items.forEach((it, i) => {
      const li = document.createElement('li');
      li.textContent = it;
      li.setAttribute('role', 'option');
      li.id = `suggest-${i}`;
      li.className = 'suggest-item';
      li.addEventListener('mousedown', (ev) => {
        ev.preventDefault();
        choose(i);
      });
      list.appendChild(li);
    });
  }

  function choose(index) {
    if (index < 0 || index >= suggestions.length) return;
    input.value = suggestions[index];
    clearSuggestions();
    
    // TỰ ĐỘNG SUBMIT FORM KHI CHỌN GỢI Ý
    const form = input.closest('form');
    if (form) {
      form.submit();
    }
  }

  function clearSuggestions() {
    suggestions = [];
    activeIndex = -1;
    list.innerHTML = '';
    list.style.display = 'none';
  }

  input.addEventListener('input', debounce((e) => {
    const q = e.target.value.trim();
    if (!q) return fetchSuggestions('');
    fetchSuggestions(q);
  }, 180));

  input.addEventListener('keydown', (e) => {
    if (!suggestions.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, suggestions.length - 1);
      highlight();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      highlight();
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0) {
        e.preventDefault();
        choose(activeIndex);
      }
    } else if (e.key === 'Escape') {
      clearSuggestions();
    }
  });

  function highlight() {
    Array.from(list.children).forEach((li, i) => {
      li.classList.toggle('active', i === activeIndex);
      if (i === activeIndex) li.scrollIntoView({block: 'nearest'});
    });
  }

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !list.contains(e.target)) {
      clearSuggestions();
    }
  });

  list.style.display = 'none';
})();
