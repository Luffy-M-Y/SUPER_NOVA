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
const btnDefine = document.getElementById('btn-define');
// Bouton RAFRAÎCHIR liste USB
// Bouton CRÉER CLÉ RECOVERY
const btnCreateUsb = document.getElementById('btn-create-usb');
// Menu déroulant pour la sélection USB
// Message retour succès/erreur création USB
const recoveryMsg = document.getElementById('recovery-msg');
let recoveryOpening = false;
let passwordCheckPromise = null;
let passwordState = null;

async function openRecoveryManager() {
  if (recoveryOpening) return;
  recoveryOpening = true;
  btnCreateUsb.disabled = true;
  btnCreateUsb.classList.add('is-loading');
  btnCreateUsb.setAttribute('aria-busy', 'true');
  btnCreateUsb.innerHTML = '<span class="spinner"></span> Ouverture en cours…';
  recoveryMsg.textContent = 'Ouverture de SUPER NOVA RECOVERY...';
  recoveryMsg.className = 'success';
  recoveryMsg.style.display = 'block';
  try {
    const [res] = await Promise.all([
      fetch('/open_recovery_manager', { method: 'POST' }),
      new Promise(resolve => setTimeout(resolve, 350))
    ]);
    const data = await res.json();
    if (!res.ok || data.error) {
      recoveryMsg.textContent = '⚠ ' + (data.error || 'Impossible d’ouvrir le gestionnaire Recovery.');
      recoveryMsg.className = 'error';
    } else {
      recoveryMsg.textContent = '✓ SUPER NOVA RECOVERY est ouvert dans une fenêtre séparée.';
      recoveryMsg.className = 'success';
    }
  } catch (error) {
    recoveryMsg.textContent = '⚠ Impossible de contacter le service local.';
    recoveryMsg.className = 'error';
  } finally {
    recoveryOpening = false;
    btnCreateUsb.disabled = false;
    btnCreateUsb.classList.remove('is-loading');
    btnCreateUsb.removeAttribute('aria-busy');
    btnCreateUsb.innerHTML = 'Ouvrir le gestionnaire Recovery';
  }
}

function openSigninSettingsAfterMessage() {
  // Laisser le navigateur afficher le message avant de changer de fenêtre.
  window.setTimeout(() => {
    fetch('/open_signin_settings', { method: 'POST' }).catch(() => {
      passMsg.textContent += ' Vérifiez les paramètres Windows manuellement.';
    });
  }, 300);
}

if (btnCreateUsb) {
  btnCreateUsb.innerHTML = 'Ouvrir le gestionnaire Recovery';
}

function renderPasswordForm(hasPassword) {
  const spinner = document.getElementById('loading-spinner');
  document.getElementById('form-define').style.display = hasPassword ? 'none' : 'block';
  document.getElementById('form-change').style.display = hasPassword ? 'block' : 'none';
  btnDefine.style.display = hasPassword ? 'none' : 'block';
  changeBtn.style.display = hasPassword ? 'block' : 'none';
  spinner.classList.remove('is-visible');
}

function loadPasswordForm() {
  if (passwordState !== null) {
    renderPasswordForm(passwordState);
    return Promise.resolve();
  }
  if (passwordCheckPromise) return passwordCheckPromise;

  const spinner = document.getElementById('loading-spinner');
  document.getElementById('form-define').style.display = 'none';
  document.getElementById('form-change').style.display = 'none';
  btnDefine.style.display = 'none';
  changeBtn.style.display = 'none';
  spinner.classList.add('is-visible');

  passwordCheckPromise = fetch('/has_password')
    .then(res => {
      if (!res.ok) throw new Error('password-check-failed');
      return res.json();
    })
    .then(data => {
      passwordState = Boolean(data.has_password);
      renderPasswordForm(passwordState);
    })
    .catch(() => {
      passMsg.textContent = '⚠ Impossible de vérifier le mot de passe.';
      passMsg.className = 'error';
      passMsg.style.display = 'block';
    })
    .finally(() => {
      spinner.classList.remove('is-visible');
      passwordCheckPromise = null;
    });

  return passwordCheckPromise;
}

// ════════════════════════════════════════
// SECTION 3 : VALIDATION CHAMPS MOT DE PASSE
// ════════════════════════════════════════
 
// Fonction : Active/désactive bouton changement selon champs remplis
// Logique :
//   - Les 3 champs (old, new, confirm) non vides → active bouton
//   - Sinon → désactive + opacité réduite + curseur not-allowed
// Appelée via : oninput="verifierChamps()" sur chaque input
function verifierChamps() {
  if (btnDefine.style.display === 'block') {
    const newPassMode = document.getElementById('define-new-pass-mode').value;
    const confirmPassMode = document.getElementById('define-confirm-pass-mode').value;
    const newPass = document.getElementById('define-new-pass').value;
    const confirmPass = document.getElementById('define-confirm-pass').value;
    
    let newPassValid = (newPassMode === 'empty') || (newPass !== '');
    let confirmPassValid = (confirmPassMode === 'empty') || (confirmPass !== '');
    
    if (newPassValid && confirmPassValid) {
      btnDefine.disabled = false;
      btnDefine.style.opacity = '1';
      btnDefine.style.cursor = 'pointer';
    } else {
      btnDefine.disabled = true;
      btnDefine.style.opacity = '0.5';
      btnDefine.style.cursor = 'not-allowed';
    }
  } else if (changeBtn.style.display === 'block') {
    const oldPassMode = document.getElementById('old-pass-mode').value;
    const newPassMode = document.getElementById('new-pass-mode').value;
    const confirmPassMode = document.getElementById('confirm-pass-mode').value;
    const oldPass = document.getElementById('old-pass').value;
    const newPass = document.getElementById('new-pass').value;
    const confirmPass = document.getElementById('confirm-pass').value;
    
    let oldPassValid = (oldPassMode === 'empty') || (oldPass !== '');
    let newPassValid = (newPassMode === 'empty') || (newPass !== '');
    let confirmPassValid = (confirmPassMode === 'empty') || (confirmPass !== '');
    
    if (oldPassValid && newPassValid && confirmPassValid) {
      changeBtn.disabled = false;
      changeBtn.style.opacity = '1';
      changeBtn.style.cursor = 'pointer';
    } else {
      changeBtn.disabled = true;
      changeBtn.style.opacity = '0.5';
      changeBtn.style.cursor = 'not-allowed';
    }
  }
}
function toggleField(fieldId) {
  const mode = document.getElementById(fieldId + '-mode').value;
  const input = document.getElementById(fieldId);
  
  if (mode === 'empty') {
    input.disabled = true;
    input.value = '';
  } else {
    input.disabled = false;
    input.focus();
  }
  verifierChamps();
}

async function showConfirm() {
  return new Promise(async (resolve) => {
    const res = await fetch('/confirmation.html');
    const html = await res.text();
    document.getElementById('modal-confirm').innerHTML = html;
    document.getElementById('modal-confirm').classList.add('active');
    
    document.getElementById('confirm-yes').onclick = () => {
      document.getElementById('modal-confirm').classList.remove('active');
      resolve(true);
    };
    document.getElementById('confirm-no').onclick = () => {
      document.getElementById('modal-confirm').classList.remove('active');
      resolve(false);
    };
  });
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
    if (tab.dataset.target === 'panel-password') {
      loadPasswordForm();
    }
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
  btn.innerHTML = '<div class="spinner"></div> Analyse en cours…';
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
    btn.innerHTML = '<span class="radar-icon"></span> Analyser le réseau';
  }
});
 
// ════════════════════════════════════════
// SECTION 6 : CHANGEMENT MOT DE PASSE
// ════════════════════════════════════════

btnDefine.addEventListener('click', async () => {
  //Recupère les valeurs des champs
  let new_Password = document.getElementById('define-new-pass').value;
  let confirm_Password = document.getElementById('define-confirm-pass').value;
  //Si les champs sont remplis
  if (new_Password && confirm_Password) {
    //Ajoute la classe CSS .scanning au bouton
    btnDefine.classList.add('scanning');
    btnDefine.innerHTML = '<div class="spinner"></div> Modification en cours…';
    //Cache les résultats précédents
    passMsg.style.display = 'none';
    panel.style.display  = 'none';

    if (await showConfirm()) {
      console.log('Changement mot de passe confirmé');
      try {
        //Envoie la requete POST vers Flask /define_password
        const res  = await fetch('/change_password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            new_password: new_Password,
            confirm_password: confirm_Password
          })
        })

        //Convertit la réponse en objet JavaScript
        const data = await res.json();

        //Traite la réponse
        if (data.open_settings) {
          passMsg.textContent   = '⚠ ' + data.error;
          passMsg.className = 'error';
          passMsg.style.display = 'block';

          // Vide les champs
          document.getElementById('define-new-pass').value = '';
          document.getElementById('define-confirm-pass').value = '';

          //Bouton desactive
          verifierChamps();
          openSigninSettingsAfterMessage();
        }
        else if (data.error == 'Les nouveaux mots de passe ne correspondent pas.'){
          passMsg.textContent   = '⚠ ' + data.error;
          passMsg.className = 'error';
          passMsg.style.display = 'block';
        }

        else if (!data.error){
          // CAS 3 : succès
          passwordState = true;
          passMsg.textContent   = '✓ Mot de passe défini avec succès !';
          passMsg.className     = 'success';  // couleur verte CSS
          passMsg.style.display = 'block';

          // Vide les champs
          document.getElementById('define-new-pass').value = '';
          document.getElementById('define-confirm-pass').value = '';

          //Bouton desactive
          verifierChamps();

          //Affiche le panel password
          panel.style.display = 'block';
        }
        else {
          passMsg.textContent = '⚠ ' + data.error;
          passMsg.className = 'error';
          passMsg.style.display = 'block';
        }

      } catch (e) {
        // CAS 4 : erreur réseau
        passMsg.textContent   = '⚠ Impossible de contacter le serveur.';
        passMsg.style.display = 'block';

      } finally {
          btnDefine.classList.remove('scanning');
          btnDefine.innerHTML = 'Définir le mot de passe';
        }
      
    }else {
        console.log('Changement mot de passe annulé');
        //Ajoute la classe CSS .scanning au bouton
        btnDefine.classList.remove('scanning');
        btnDefine.innerHTML = 'Définir le mot de passe';
      }
  }
})
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
  changeBtn.innerHTML = '<div class="spinner"></div> Modification en cours…';
  // Cache les résultats précédents
  passMsg.style.display = 'none';
  panel.style.display  = 'none';

  if (await showConfirm()) { 
    console.log('Changement mot de passe confirmé');
    try {
      // ── Étape 3 : envoie requête POST vers Flask /change_password ──
      // fetch('/change_password', {...}) = envoie POST avec données
      // method: 'POST' = type de requête
      // headers: Content-Type = dit au serveur "c'est du JSON"
      // body: JSON.stringify() = convertit données JS en chaîne JSON
        // envoyer requête
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
      if (data.open_settings) {
        // CAS 1 : compte Microsoft détecté
        // Le message est affiché avant la demande d'ouverture des paramètres.
        passMsg.textContent   = '⚠ ' + data.error;
        passMsg.className     = 'error';  // couleur rouge CSS
        passMsg.style.display = 'block';
        
        // Vide les champs
        document.getElementById('old-pass').value = '';
        document.getElementById('new-pass').value = '';
        document.getElementById('confirm-pass').value = '';
        
        // Désactive bouton (champs maintenant vides)
        verifierChamps();
        openSigninSettingsAfterMessage();
  
      } else if (data.error == 'Mot de passe actuel incorrect') {
        // CAS 2 : mot de passe actuel incorrect
        passMsg.textContent   = '⚠ ' + data.error;
        passMsg.className     = 'error';  // couleur rouge CSS
        passMsg.style.display = 'block';
        
        // Vide uniquement le champ du mot de passe actuel
        document.getElementById('old-pass').value = '';
        
        // Désactive bouton (champ old-password maintenant vide)
        verifierChamps();
        
      } else if (data.error == 'Les nouveaux mots de passe ne correspondent pas.'){
        // CAS 3 : nouveau mot de passe et confirmation ne correspondent pas
        passMsg.textContent   = '⚠ ' + data.error;
        passMsg.className     = 'error';  // couleur rouge CSS
        passMsg.style.display = 'block';
      } else if (data.error) {
        passMsg.textContent = '⚠ ' + data.error;
        passMsg.className = 'error';
        passMsg.style.display = 'block';
        // vide champs
      } 
      else if (data.success){
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
        changeBtn.innerHTML = 'Changer le mot de passe';
    }
  }
  else {
    console.log('Changement mot de passe annulé');
    // Remet bouton à l'état initial
    changeBtn.classList.remove('scanning');
    changeBtn.innerHTML = 'Changer le mot de passe';
  }
  });

// Le gestionnaire local possède sa propre interface et sa propre sélection USB.
// Le bouton du panneau Recovery ouvre donc directement cette interface.
if (btnCreateUsb) {
  btnCreateUsb.addEventListener('click', openRecoveryManager);
}
