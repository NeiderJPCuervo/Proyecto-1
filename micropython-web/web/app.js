// Lógica de la página: pide las lecturas a la API cada pocos segundos y las muestra.
const API = "/api/datos";
const INTERVALO_MS = 5000;

const $ = (id) => document.getElementById(id);

function formatearFecha(iso) {
  return new Date(iso).toLocaleString("es-CO");
}

function celda(texto) {
  const td = document.createElement("td");
  td.textContent = texto; // textContent evita inyección de HTML
  return td;
}

function pintarTabla(lecturas) {
  const tbody = $("tabla");
  tbody.replaceChildren();
  for (const l of lecturas) {
    const tr = document.createElement("tr");
    tr.append(
      celda(l.id),
      celda(l.dispositivo),
      celda(l.temperatura),
      celda(l.humedad ?? "—"),
      celda(formatearFecha(l.recibido))
    );
    tbody.append(tr);
  }
}

function pintarGrafica(lecturas) {
  const canvas = $("grafica");
  const ctx = canvas.getContext("2d");
  const ancho = (canvas.width = canvas.clientWidth * devicePixelRatio);
  const alto = (canvas.height = 220 * devicePixelRatio);
  ctx.clearRect(0, 0, ancho, alto);

  const puntos = lecturas.slice().reverse(); // de la más antigua a la más reciente
  if (puntos.length < 2) return;

  const temps = puntos.map((l) => l.temperatura);
  let min = Math.min(...temps);
  let max = Math.max(...temps);
  if (max - min < 1) { min -= 0.5; max += 0.5; }

  const margen = 30 * devicePixelRatio;
  const x = (i) => margen + (i * (ancho - 2 * margen)) / (puntos.length - 1);
  const y = (t) => alto - margen - ((t - min) * (alto - 2 * margen)) / (max - min);

  const estilo = getComputedStyle(document.documentElement);
  ctx.font = `${12 * devicePixelRatio}px system-ui`;
  ctx.fillStyle = estilo.getPropertyValue("--suave");
  ctx.fillText(`${max.toFixed(1)} °C`, 4, margen - 8);
  ctx.fillText(`${min.toFixed(1)} °C`, 4, alto - 8);

  ctx.strokeStyle = estilo.getPropertyValue("--acento");
  ctx.lineWidth = 2 * devicePixelRatio;
  ctx.beginPath();
  puntos.forEach((l, i) => (i ? ctx.lineTo(x(i), y(l.temperatura)) : ctx.moveTo(x(i), y(l.temperatura))));
  ctx.stroke();
}

async function actualizar() {
  try {
    const respuesta = await fetch(`${API}?limite=50`);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
    const lecturas = await respuesta.json();

    $("estado").textContent = `En línea · ${lecturas.length} lecturas`;
    $("estado").className = "estado ok";

    const ultima = lecturas[0];
    $("temp-actual").textContent = ultima ? ultima.temperatura : "--";
    $("hum-actual").textContent = ultima?.humedad ?? "--";
    $("ultima").textContent = ultima ? `${ultima.dispositivo} · ${formatearFecha(ultima.recibido)}` : "Sin datos aún";

    pintarTabla(lecturas);
    pintarGrafica(lecturas);
  } catch (error) {
    $("estado").textContent = "Sin conexión con la API";
    $("estado").className = "estado error";
    console.error(error);
  }
}

$("formulario").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = new FormData(evento.target);
  const datos = {
    dispositivo: form.get("dispositivo"),
    temperatura: Number(form.get("temperatura")),
  };
  if (form.get("humedad") !== "") datos.humedad = Number(form.get("humedad"));

  const mensaje = $("mensaje");
  try {
    const respuesta = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    });
    const cuerpo = await respuesta.json();
    if (!respuesta.ok) throw new Error(cuerpo.error || `HTTP ${respuesta.status}`);
    mensaje.textContent = `Dato guardado (id ${cuerpo.id})`;
    mensaje.className = "ok";
    actualizar();
  } catch (error) {
    mensaje.textContent = `Error: ${error.message}`;
    mensaje.className = "error";
  }
});

window.addEventListener("resize", actualizar);
actualizar();
setInterval(actualizar, INTERVALO_MS);
