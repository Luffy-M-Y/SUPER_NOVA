// On récupère les éléments HTML qu'on va manipuler.
// getElementById retourne l'élément dont l'id correspond.
const btn    = document.getElementById('btn-scan');
const panel  = document.getElementById('result-panel');
const errMsg = document.getElementById('error-msg');
const signal = document.getElementById('signal');

// addEventListener('click', ...) : on "écoute" le clic sur le bouton.
// async () => {} : fonction asynchrone — elle peut utiliser await à l'intérieur.
btn.addEventListener('click', async () => {

  // ── Étape 1 : état visuel "en cours de scan" ──
  // On ajoute la classe CSS .scanning → bouton passe en vert avec animation pulse. 
  btn.classList.add('scanning');
  btn.innerHTML = '<span class="radar-icon"></span> SCANNING...';
  // On cache les résultats précédents le temps du nouveau scan.
  errMsg.style.display = 'none';
  panel.style.display  = 'none';

  try {
    // ── Étape 2 : appel vers Flask ──
    // fetch('/scan') envoie une requête HTTP GET à la route /scan de Flask.
    // await → JS attend la réponse avant de continuer (sans bloquer la page).
    const res  = await fetch('/scan');

    // res.json() lit le corps de la réponse et le convertit en objet JS.
    // Flask renvoie quelque chose comme : { "ssid": "MonWifi", "password": "abc123", "security": "WPA2" }
    // Après cette ligne, data est un objet JS normal qu'on peut lire avec data.ssid etc.
    const data = await res.json();

    // ── Étape 3 : 2 cas possibles ──

    if (data.error) {
      // CAS 1 — Flask a renvoyé { "error": "message d'erreur" }
      // Ex: pas connecté au WiFi, pas les droits admin, etc.
      errMsg.textContent   = '⚠ ' + data.error;
      errMsg.style.display = 'block';  // on rend le message visible

    } else {
      // CAS 2 — Flask a renvoyé les données WiFi correctement.
      // On injecte chaque valeur dans le bon élément HTML via textContent.
      // || '—' : si la valeur est vide/undefined, on affiche '—' par défaut.
      document.getElementById('val-ssid').textContent = data.ssid     || '—';
      document.getElementById('val-pass').textContent = data.password || '(non trouvé)';
      document.getElementById('val-sec').textContent  = data.security || '—';

      // On rend le panel visible maintenant que les données sont prêtes.
      panel.style.display = 'block';

      // On allume la 4e barre de signal en vert (classe .active dans le CSS).
      signal.classList.add('active');
    }

  } catch (e) {
    // CAS 3 — fetch() a échoué complètement : Flask n'est pas lancé,
    // ou problème réseau. L'erreur est capturée ici par le catch.
    errMsg.textContent   = '⚠ Impossible de contacter le serveur.';
    errMsg.style.display = 'block';

  } finally {
    // finally s'exécute TOUJOURS, que ce soit un succès ou une erreur.
    // On remet le bouton à son état initial.
    btn.classList.remove('scanning');
    btn.innerHTML = '<span class="radar-icon"></span> SCAN NETWORK';
  }
});
