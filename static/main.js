'use strict';

function imagePreviewHandler(event) {
    if (event.target.files && event.target.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = document.querySelector('.background-preview > img');
            img.src = e.target.result;
            if (img.classList.contains('d-none')) {
                const label = document.querySelector('.background-preview > label');
                label.classList.add('d-none');
                img.classList.remove('d-none');
            }
        };
        reader.readAsDataURL(event.target.files[0]);
    }
}

function openLink(event) {
    const row = event.target.closest('.row');
    if (row && row.dataset.url) {
        window.location = row.dataset.url;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const deleteModalEl = document.getElementById('deleteModal');
    if (deleteModalEl) {
        deleteModalEl.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const url = button.getAttribute('data-url');
            const title = button.getAttribute('data-title');
            const form = deleteModalEl.querySelector('form');
            const span = deleteModalEl.querySelector('.delete-title');

            form.action = url;
            span.textContent = title;
        });
    }

    const backgroundImgField = document.getElementById('background_img');
    if (backgroundImgField) {
        backgroundImgField.addEventListener('change', imagePreviewHandler);
    }

    document.querySelectorAll('.book-list .row').forEach(courseElm => {
        courseElm.addEventListener('click', openLink);
    });
});
