function Show(btn) {
  const targetId = btn.dataset.target;
  const input = document.getElementById(targetId);
  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}

// On récupère les éléments HTML qu'on va manipuler.
const btn     = document.getElementById('btn-scan');
const panel   = document.getElementById('result-panel');
const errMsg  = document.getElementById('error-msg');
const passMsg = document.getElementById('pass-msg');
const signal  = document.getElementById('signal');
const changeBtn = document.getElementById('btn-change');

function verifierChamps() {
  const old     = document.getElementById('old-pass').value;
  const nouveau = document.getElementById('new-pass').value;
  const confirm = document.getElementById('confirm-pass').value;

  // Si les 3 sont non vides → active le bouton, sinon désactive
  if (old && nouveau && confirm) {
    changeBtn.disabled     = false;
    changeBtn.style.opacity = '1';
    changeBtn.style.cursor  = 'pointer';
  } else {
    changeBtn.disabled     = true;
    changeBtn.style.opacity = '0.5';
    changeBtn.style.cursor  = 'not-allowed';
  }
}

// ── Logique des onglets ──
// querySelectorAll retourne TOUS les éléments avec la classe .tab (un tableau).
// On boucle dessus avec forEach pour ajouter un écouteur de clic sur chacun.
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    // Retire .tab-active de tous les onglets
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('tab-active'));
    // Cache tous les panels
    document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
    // Active l'onglet cliqué
    tab.classList.add('tab-active');
    // Affiche le panel correspondant — data-target dans le HTML indique quel id afficher
    document.getElementById(tab.dataset.target).style.display = 'block';
  });
});

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

// addEventListener('click', ...) : on "écoute" le clic sur le bouton.
// async () => {} : fonction asynchrone — elle peut utiliser await à l'intérieur.
changeBtn.addEventListener('click', async () => {
  // Recuperation des valeurs du mot de passe 
  let old_Password = document.getElementById('old-pass').value;
  let new_Password = document.getElementById('new-pass').value;
  let confirm_Password = document.getElementById('confirm-pass').value;

  // ── Étape 1 : état visuel "en cours de scan" ──
  // On ajoute la classe CSS .scanning → bouton passe en vert avec animation pulse. 
  changeBtn.classList.add('scanning');
  changeBtn.innerHTML = '<span class="radar-icon"></span> CHANGING...';
  // On cache les résultats précédents le temps du nouveau scan.
  passMsg.style.display = 'none';
  panel.style.display  = 'none';

  try {
    // ── Étape 2 : appel vers Flask ──
    // fetch('/scan') envoie une requête HTTP GET à la route /scan de Flask.
    // await → JS attend la réponse avant de continuer (sans bloquer la page).
    const res  = await  fetch('/change_password', {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json'
                              },
                              body: JSON.stringify({
                                old_password: old_Password,
                                new_password: new_Password,
                                confirm_password: confirm_Password
                              })
                            })

    // res.json() lit le corps de la réponse et le convertit en objet JS.
    // Flask renvoie quelque chose comme : { "ssid": "MonWifi", "password": "abc123", "security": "WPA2" }
    // Après cette ligne, data est un objet JS normal qu'on peut lire avec data.ssid etc.
    const data = await res.json();

    // ── Étape 3 : 2 cas possibles ──

    if (data.error) {
      // CAS 1 — Flask a renvoyé { "error": "message d'erreur" }
      // Ex: Compte microsof trouvé, pas les droits admin, etc.
      passMsg.textContent   = '⚠ ' + data.error;
      passMsg.className     = 'error';
      passMsg.style.display = 'block';  // on rend le message visible
      document.getElementById('old-pass').value = '';
      document.getElementById('new-pass').value = '';
      document.getElementById('confirm-pass').value = '';
      verifierChamps()


    } else {
      // CAS 2 — Flask a renvoyé les données WiFi correctement.
      // On injecte chaque valeur dans le bon élément HTML via textContent.
      // || '—' : si la valeur est vide/undefined, on affiche '—' par défaut.
      passMsg.textContent    = 'Password changed successfully!';
      passMsg.className      = 'success';  // applique la couleur verte du CSS
      passMsg.style.display  = 'block';
      document.getElementById('old-pass').value = '';
      document.getElementById('new-pass').value = '';
      document.getElementById('confirm-pass').value = '';
    }

  } catch (e) {
    // CAS 3 — fetch() a échoué complètement : Flask n'est pas lancé,
    // ou problème réseau. L'erreur est capturée ici par le catch.
    passMsg.textContent   = '⚠ Impossible de contacter le serveur.';
    passMsg.style.display = 'block';

  } finally {
    // finally s'exécute TOUJOURS, que ce soit un succès ou une erreur.
    // On remet le bouton à son état initial.
    changeBtn.classList.remove('scanning');
    changeBtn.innerHTML = '<span class="radar-icon"></span> CHANGE PASSWORD';
  }
});