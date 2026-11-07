# junction26
Collaboration project for the group MixedSignals


Ohjeet GITin käyttämiseen:

Aloitus:
1) Avaa pääte laitteessasi.
2) lataa GIT:
    
"How to Install by Operating System

• Windows: Go to Git for Windows to download the standalone installer for x64 or ARM64, or use package managers via winget install --id Git.Git -e --source winget.
• macOS: Install via Homebrew using brew install git, via MacPorts with sudo port install git, or through Xcode Command Line Tools (xcode-select --install).
• Linux: Use your distribution's package manager, such as sudo apt install git-all on Ubuntu/Debian or sudo dnf install git-all on Fedora."- Google Search AI

4) Tee lokaali kansio  esim. "junction" nimellä (ei väliä, näkyy vaan sulle)

5) Kopioi SSH-linkki täältä GitHubin reposta leikepöydälle: mene repositoryyn -> klikkaa code -> kopioi ssh-linkki

6) Nyt kun GIT on ladattuna, voit käyttää git-komentoja...Aja komento git clone ssh-linkki tekemässäsi lokaalissa kansiossa -> Nyt sulla on meidän yhteinen projekti ja voit tehdä siihen muutoksia. (Älä kuitenkaan vielä tee)

7) Lataa uv (environment manager):

   Windows powershellissä: "irm https://astral.sh/uv/install.ps1 | iex"

   Linux terminaalissa: "curl -LsSf https://astral.sh/uv/install.sh | sh"

9) lataa python virtuaaliympäristöön
   
   uv python install
   
   uv sync --locked

Workflow yleisesti:
 - Käytetään gittiä versionhallintajärjestelmänä ja koodin jakamisessa keskenämme
 - Tehdään projektissa vastuualueet projektin eri vaiheille jo suunnitteluvaiheessa
 - Jokainen työstää projektia omalla branchillaan ja kun projektissa on toimiva osakokonaisuus, yhdistetään branchit main-branchiin.         Ideana on koittaa välttää merge-conflicteja tällasella systeemillä 
 - Tähän tarvitaan muutama git-komento, jotka käydään läpi seuraavaksi

git-workflow:

1) vain alussa on ajettu git clone. Sitä ei enää tehdä.

2) Luo oma branch:

   git checkout -b uusi_branch main // tietyssä brancheissa tehdyt muutokset näkyy vain siinä branchissa

4) Kun olet saanut jotain aikaan, ne siirretään GitHubiin seuraavasti:
   
   I) git add muutettu_tiedosto1 muutettu_tiedosto2 ...
   
   II) git status
   
   II) git commit -m  "moromoro"
   
   III) git push origin branchin_nimi
   
6) 
    Jos tarvitset jonkun toisen vastuualueen koodia, täytyy ajaa:

   I) git switch oma_branch // vaihda omaan brachiin

   II) git pull origin branchin_nimi // hae viimeiset pushatut muutokset toisen branchista ja mergaa ne omaan

8) Merge main branchiin:
   
   Pidetään huolta, että merge main branchiin on aina yhdessä sovittu, eli käytännössä kun yksi vaihe projektia on saatu tehtyä. Tällä tavoin pystymme yrittää välttää merge conflicteja. Niiden ratkominen vie yleensä aikaa.

9) Kun siirrytään seuraavaan vaiheeseen, aletaan työstää mergattua mainia. Nyt se täytyy pullata:
 
    I) git switch main //vaihda mainiin

    II) git pull origin main // pullaa main

    III) git switch oma_branch // vaihda omaan branhciin
   
    IV) git merge main // mergaa maini omaan branchiin


Tämän jälkeen iteroidaan vaiheita 2-6.

Cheat sheet:
<table> <thead> <tr> <th>Situation</th> <th>Command</th> </tr> </thead> <tbody> <tr> <td>Clone repository (first time only)</td> <td><code>git clone &lt;ssh-link&gt;</code></td> </tr> <tr> <td>Install required Python version</td> <td><code>uv python install</code></td> </tr> <tr> <td>Set up / synchronize Python environment</td> <td><code>uv sync --locked</code></td> </tr> <tr> <td>Check local changes</td> <td><code>git status</code></td> </tr> <tr> <td>See actual unstaged changes</td> <td><code>git diff</code></td> </tr> <tr> <td>See staged changes</td> <td><code>git diff --staged</code></td> </tr> <tr> <td>List local branches</td> <td><code>git branch</code></td> </tr> <tr> <td>Create new branch and switch to it</td> <td><code>git checkout -b oma_branch main</code></td> </tr> <tr> <td>Stage specific files</td> <td><code>git add file1 file2 ...</code></td> </tr> <tr> <td>Commit changes</td> <td><code>git commit -m "Description"</code></td> </tr> <tr> <td>Push your branch to GitHub</td> <td><code>git push origin oma_branch</code></td> </tr> <tr> <td>Pull another person's branch into your own</td> <td> <code>git switch oma_branch</code><br> <code>git pull origin wanted_branch</code> </td> </tr> <tr> <td>Switch to main</td> <td><code>git switch main</code></td> </tr> <tr> <td>Update main from GitHub</td> <td><code>git pull origin main</code></td> </tr> <tr> <td>Merge updated main into your own branch</td> <td> <code>git switch oma_branch</code><br> <code>git merge main</code> </td> </tr> <tr> <td>Add a new Python library</td> <td><code>uv add library_name</code></td> </tr> <tr> <td>Remove a Python library</td> <td><code>uv remove library_name</code></td> </tr> </tbody> </table>

Ohjeet koodin testaukseen:

- Kun teet funktioita tai luokkia pythonissa ja haluat testata niitä, kirjoita testi-koodi seuraavasti tiedoston loppuun:
  
  if __name__ == "__main__":

      testaa(funktio1())

  Tällöin python ajaa testikoodin vain kun ajat kyseisen tiedoston python-interpreterillä. Jos tiedostoa     käytetään kirjastona toisessa ohjelmassa, testikoodia ei ajeta.


      


