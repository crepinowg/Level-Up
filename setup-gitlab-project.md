## Configuration d'un projet GitLab local

### Étapes à suivre :
1. **Cloner le dépôt distant**
   ```bash
   git clone https://gitlab.com/votre-username/votre-projet.git
   ```
2. **Naviguer dans le répertoire**
   ```bash
   cd votre-projet
   ```
3. **Configurer les identifiants Git**
   ```bash
   git config --global user.name "VotreNom"
   git config --global user.email "votre@email.com"
   ```
4. **Ajouter des modifications**
   ```bash
   git add .
   ```
5. **Commiter les changements**
   ```bash
   git commit -m "Message de commit"
   ```
6. **Pousser vers GitLab**
   ```bash
   git push origin main
   ```