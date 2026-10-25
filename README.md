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
5) Kopioi SSH-linkki täältä GitHubin reposta leikepöydälle
6) Nyt kun GIT on ladattuna, voit käyttää git-komentoja...Aja komento "git clone <ssh-linkki>" tekemässäsi lokaalissa kansiossa -> Nyt sulla on meidän yhteinen projekti ja voit tehdä siihen muutoksia. (Älä kuitenkaan vielä tee)

Workflow yleisesti:
 - Käytetään gittiä versionhallintajärjestelmänä ja koodin jakamisessa keskenämme
 - Tehdään projektissa vastuualueet projektin eri vaiheille jo suunnitteluvaiheessa
 - Jokainen työstää projektia omalla branchillaan ja kun projektissa on toimiva osakokonaisuus, yhdistetään branchit main-branchiin. -> Tällä tavalla ei synny merge-conflicteja, mitkä voi olla iso ongelma yhteisessä projekteissa, ja sit toisaalta saadaan jaettua koodia nopeasti.
 - Tähän tarvitaan muutama git-komento, jotka käydään läpi seuraavaksi

git-workflow:
1) vain alussa on ajettu git clone. Sitä ei enää tehdä.
2) Luo oma branch: "git checkout -b <uusi_branch> main" -> eri brancheissa tehdyt muutokset näkyy vain siinä branchissa

//tee muutoksia

3) Kun olet saanut jotain aikaan, ne siirretään GitHubiin seuraavasti:
   I) git add <muutettu_tiedosto1> <muutettu_tiedosto2> ...
   II) git commit -m  "moromoro"
   III) git push origin <branchin_nimi>
4) 
    Jos tarvitset jonkun toisen vastuualueen koodia, täytyy ajaa
   "git pull origin <branchin_nimi>" // 
   "git switch <oma_branch> //tämä sen takia että et vahingossa tee mergeä mihinkään muuhun branchiin
   "git merge origin <branchin_nimi> // 
   HUOM! 

Kun
   
   
