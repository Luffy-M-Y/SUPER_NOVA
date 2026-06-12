// ════════════════════════════════════════
// SECTION 1 : BASCULER VISIBILITÉ MOT DE PASSE
// ════════════════════════════════════════
 
// Fonction : Affiche/masque mot de passe au clic sur l'œil
// Paramètre : btn = bouton cliqué
// Utilise : btn.dataset.target → id de l'input à modifier (data-target="old-pass")
// Logique : toggle type password ↔ text
function Show(btn) {
  const targetId = btn.dataset.target;
  const input = document.getElementById(targetId);
  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}
 
// ════════════════════════════════════════
// SECTION 2 : RÉCUPÉRATION ÉLÉMENTS DOM
// ════════════════════════════════════════
 
// Bouton SCAN NETWORK
const btn     = document.getElementById('btn-scan');
// Panel affichage résultats WiFi
const panel   = document.getElementById('result-panel');
// Message erreur scan WiFi
const errMsg  = document.getElementById('error-msg');
// Message succès/erreur changement mdp
const passMsg = document.getElementById('pass-msg');
// Icône barres de signal WiFi
const signal  = document.getElementById('signal');
// Bouton CHANGE PASSWORD
const changeBtn = document.getElementById('btn-change');
 
// ════════════════════════════════════════
// SECTION 3 : VALIDATION CHAMPS MOT DE PASSE
// ════════════════════════════════════════
 
// Fonction : Active/désactive bouton changement selon champs remplis
// Logique :
//   - Les 3 champs (old, new, confirm) non vides → active bouton
//   - Sinon → désactive + opacité réduite + curseur not-allowed
// Appelée via : oninput="verifierChamps()" sur chaque input
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
 
// ════════════════════════════════════════
// SECTION 4 : SYSTÈME D'ONGLETS
// ════════════════════════════════════════
 
// Logique : Bascule entre onglets WIFI et MOT DE PASSE
// Sélectionne : tous les éléments avec classe .tab
// Pour chaque onglet : ajoute écouteur de clic
// Au clic :
//   1. Retire classe tab-active de TOUS les onglets
//   2. Cache TOUS les panels (display: none)
//   3. Ajoute classe tab-active à l'onglet cliqué
//   4. Affiche panel correspondant (data-target="id-du-panel")
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
 
// ════════════════════════════════════════
// SECTION 5 : SCAN RÉSEAU WIFI
// ════════════════════════════════════════
 
// Écouteur : au clic sur le bouton SCAN NETWORK
// Fonction : async = peut utiliser await pour requêtes asynchrones
btn.addEventListener('click', async () => {
 
  // ── Étape 1 : changement visuel "scanning" ──
  // Ajoute classe CSS .scanning → bouton vert + animation pulse
  btn.classList.add('scanning');
  btn.innerHTML = '<span class="radar-icon"></span> SCANNING...';
  // Cache les résultats précédents
  errMsg.style.display = 'none';
  panel.style.display  = 'none';
 
  try {
    // ── Étape 2 : requête vers Flask /scan ──
    // fetch('/scan') = envoie GET à la route /scan
    // await = attendre réponse avant continuer
    const res  = await fetch('/scan');
 
    // res.json() = convertir réponse en objet JavaScript
    // Flask retourne : { "ssid": "MonWifi", "password": "abc123", "security": "WPA2" }
    const data = await res.json();
 
    // ── Étape 3 : traite réponse ──
 
    if (data.error) {
      // CAS 1 : erreur (pas connecté, pas d'admin, etc)
      errMsg.textContent   = '⚠ ' + data.error;
      errMsg.style.display = 'block';
 
    } else {
      // CAS 2 : succès → affiche résultats
      // Remplit chaque champ HTML avec données Flask
      // || '—' = valeur par défaut si vide/undefined
      document.getElementById('val-ssid').textContent = data.ssid     || '—';
      document.getElementById('val-pass').textContent = data.password || '(non trouvé)';
      document.getElementById('val-sec').textContent  = data.security || '—';
 
      // Affiche panel résultats
      panel.style.display = 'block';
 
      // Colore la 4e barre de signal en vert (classe .active CSS)
      signal.classList.add('active');
    }
 
  } catch (e) {
    // CAS 3 : erreur réseau (Flask pas lancé, etc)
    errMsg.textContent   = '⚠ Impossible de contacter le serveur.';
    errMsg.style.display = 'block';
 
  } finally {
    // s'exécute TOUJOURS (succès ou erreur)
    // Remet bouton à l'état initial
    btn.classList.remove('scanning');
    btn.innerHTML = '<span class="radar-icon"></span> SCAN NETWORK';
  }
});
 
// ════════════════════════════════════════
// SECTION 6 : CHANGEMENT MOT DE PASSE
// ════════════════════════════════════════
 
// Écouteur : au clic sur le bouton CHANGE PASSWORD
// Fonction : async = peut utiliser await pour requêtes asynchrones
changeBtn.addEventListener('click', async () => {
  
  // ── Étape 1 : récupère valeurs champs ──
  let old_Password = document.getElementById('old-pass').value;
  let new_Password = document.getElementById('new-pass').value;
  let confirm_Password = document.getElementById('confirm-pass').value;
 
  // ── Étape 2 : changement visuel "changing" ──
  // Ajoute classe CSS .scanning → bouton vert + animation pulse
  changeBtn.classList.add('scanning');
  changeBtn.innerHTML = '<span class="radar-icon"></span> CHANGING...';
  // Cache les résultats précédents
  passMsg.style.display = 'none';
  panel.style.display  = 'none';
 
  try {
    // ── Étape 3 : envoie requête POST vers Flask /change_password ──
    // fetch('/change_password', {...}) = envoie POST avec données
    // method: 'POST' = type de requête
    // headers: Content-Type = dit au serveur "c'est du JSON"
    // body: JSON.stringify() = convertit données JS en chaîne JSON
    const res  = await fetch('/change_password', {
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
 
    // res.json() = convertir réponse en objet JavaScript
    // Flask retourne :
    //   - Succès : {"success": true}
    //   - Erreur : {"error": "message d'erreur"}
    const data = await res.json();
 
    // ── Étape 4 : traite réponse ──
 
    // Vérification spéciale : compte Microsoft (redirection Settings)
    if (data.error == 'Compte Microsoft détecté. Redirection vers Windows Settings...') {
      // CAS 1 : compte Microsoft détecté
      // Windows Settings s'ouvre automatiquement côté serveur
      // Message à l'utilisateur : l'erreur reçue
      passMsg.textContent   = '⚠ ' + data.error;
      passMsg.className     = 'error';  // couleur rouge CSS
      passMsg.style.display = 'block';
      
      // Vide les champs
      document.getElementById('old-pass').value = '';
      document.getElementById('new-pass').value = '';
      document.getElementById('confirm-pass').value = '';
      
      // Désactive bouton (champs maintenant vides)
      verifierChamps();
 
    } 
    else if (data.error == 'Mot de passe actuel incorrect') {
      // CAS 2 : mot de passe actuel incorrect
      passMsg.textContent   = '⚠ ' + data.error;
      passMsg.className     = 'error';  // couleur rouge CSS
      passMsg.style.display = 'block';
      
      // Vide uniquement le champ du mot de passe actuel
      document.getElementById('old-pass').value = '';
      
      // Désactive bouton (champ old-password maintenant vide)
      verifierChamps();
      
    }
    else if (data.error == 'Les nouveaux mots de passe ne correspondent pas.'){
      // CAS 3 : nouveau mot de passe et confirmation ne correspondent pas
      passMsg.textContent   = '⚠ ' + data.error;
      passMsg.className     = 'error';  // couleur rouge CSS
      passMsg.style.display = 'block';
    }
    else{
      // CAS 4 : succès
      passMsg.textContent   = '✓ Mot de passe changé avec succès !';
      passMsg.className     = 'success';  // couleur verte CSS
      passMsg.style.display = 'block';

      // Vide les champs
      document.getElementById('old-pass').value = '';
      document.getElementById('new-pass').value = '';
      document.getElementById('confirm-pass').value = '';

      // Désactive bouton (champs maintenant vides)
      verifierChamps();

      // Affiche panel password
      panel.style.display = 'block';
    }
} catch (e) {
    // CAS 3 : erreur réseau (Flask pas lancé, etc)
    passMsg.textContent   = '⚠ Impossible de contacter le serveur.';
    passMsg.style.display = 'block';
 
  } finally {
    // s'exécute TOUJOURS (succès ou erreur)
    // Remet bouton à l'état initial
    changeBtn.classList.remove('scanning');
    changeBtn.innerHTML = '<span class="radar-icon"></span> CHANGE PASSWORD';
  }
});