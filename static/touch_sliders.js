(function() {
    function setRangeFromPointer(slider, clientX) {
        const rect = slider.getBoundingClientRect();
        const width = Math.max(1, rect.width);
        const position = Math.max(0, Math.min(width, clientX - rect.left));
        const min = Number(slider.min || 0);
        const max = Number(slider.max || 100);
        const step = Number(slider.step || 1);
        let value = min + (position / width) * (max - min);

        if (step > 0) {
            value = Math.round(value / step) * step;
        }

        value = Math.max(min, Math.min(max, value));
        slider.value = String(Math.round(value));
        slider.dispatchEvent(new Event('input', { bubbles: true }));
        slider.dispatchEvent(new Event('change', { bubbles: true }));
    }

    document.addEventListener('pointerdown', function(event) {
        const slider = event.target.closest('input[type="range"]');
        if (!slider) {
            return;
        }

        slider.setPointerCapture?.(event.pointerId);
        setRangeFromPointer(slider, event.clientX);
    });

    document.addEventListener('pointermove', function(event) {
        const slider = event.target.closest('input[type="range"]');
        if (!slider || event.buttons !== 1) {
            return;
        }

        setRangeFromPointer(slider, event.clientX);
    });
})();
