/* Validación en el navegador.
 *
 * Es comodidad: avisa antes de enviar y evita el viaje al servidor. La
 * validación que manda es la del servidor, porque estos atributos solo los
 * respeta el navegador y una petición armada a mano no pasa por ninguno.
 *
 * El listener va sobre el documento en fase de captura, así cubre también los
 * formularios que se arman con JavaScript después de cargar la página.
 */
(function () {
    'use strict';

    document.addEventListener('submit', function (evento) {
        var form = evento.target;
        if (!form.classList || !form.classList.contains('needs-validation')) {
            return;
        }
        if (!form.checkValidity()) {
            evento.preventDefault();
            evento.stopPropagation();
            var primero = form.querySelector(':invalid');
            if (primero) {
                primero.focus();
                primero.scrollIntoView({ block: 'center', behavior: 'smooth' });
            }
        }
        form.classList.add('was-validated');
    }, true);

    /* La identificación se escribe distinto según el tipo: una cédula solo admite
     * dígitos y un pasaporte admite letras. Se refleja en el campo para que el
     * teclado del móvil y el aviso coincidan con lo que el servidor va a exigir. */
    var REGLAS_DOCUMENTO = {
        '11': { patron: '[0-9]{6,15}', numerico: true,  aviso: 'El registro civil son entre 6 y 15 dígitos.' },
        '12': { patron: '[0-9]{6,15}', numerico: true,  aviso: 'La tarjeta de identidad son entre 6 y 15 dígitos.' },
        '13': { patron: '[0-9]{4,10}', numerico: true,  aviso: 'La cédula son entre 4 y 10 dígitos, sin puntos.' },
        '21': { patron: '[A-Za-z0-9]{4,20}', numerico: false, aviso: 'Entre 4 y 20 letras o números.' },
        '22': { patron: '[A-Za-z0-9]{4,20}', numerico: false, aviso: 'Entre 4 y 20 letras o números.' },
        '31': { patron: '[0-9]{8,10}', numerico: true,  aviso: 'El NIT son entre 8 y 10 dígitos, sin el de verificación.' },
        '41': { patron: '[A-Za-z0-9]{5,20}', numerico: false, aviso: 'El pasaporte admite letras y números.' },
        '42': { patron: '[A-Za-z0-9]{3,30}', numerico: false, aviso: 'Entre 3 y 30 letras o números.' },
        '50': { patron: '[A-Za-z0-9]{3,30}', numerico: false, aviso: 'Entre 3 y 30 letras o números.' },
        '91': { patron: '[0-9]{6,15}', numerico: true,  aviso: 'El NUIP son entre 6 y 15 dígitos.' }
    };

    function ajustarDocumento() {
        var tipo = document.querySelector('select[name="document_type"]');
        var numero = document.querySelector('input[name="document_number"]');
        if (!tipo || !numero) {
            return;
        }

        function aplicar() {
            var regla = REGLAS_DOCUMENTO[tipo.value];
            if (!regla) {
                numero.removeAttribute('pattern');
                numero.removeAttribute('inputmode');
                return;
            }
            numero.setAttribute('pattern', regla.patron);
            numero.setAttribute('inputmode', regla.numerico ? 'numeric' : 'text');
            numero.setAttribute('title', regla.aviso);
            var hueco = numero.parentNode.querySelector('.invalid-feedback:not(.d-block)');
            if (hueco) {
                hueco.textContent = regla.aviso;
            }
        }

        tipo.addEventListener('change', aplicar);
        aplicar();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ajustarDocumento);
    } else {
        ajustarDocumento();
    }
})();
