# junction26
MixedSignals-tiimin projekti


# Ohjeet tarvittavien työkalujen lataamiseen ja projektin alustamiseen tietokoneellasi:

1) Avaa pääte laitteessasi.
2) lataa GIT:
    [GIT asennus](https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://git-scm.com/install/&ved=2ahUKEwiir7axrfaXAxW_JxAIHSBJIksQFnoECBEQAQ&usg=AOvVaw1piXI91x_chH4u0QiwVJRs)


4) Tee lokaali kansio  esim. "junction" nimellä (ei väliä, näkyy vaan sulle)

5) Kopioi SSH-linkki täältä GitHubin reposta leikepöydälle: mene repositoryyn -> klikkaa code -> kopioi ssh-linkki

6) Nyt kun GIT on ladattuna, voit käyttää git-komentoja. Aja ```git clone <ssh-linkki>```
   tekemässäsi lokaalissa kansiossa -> Nyt sulla on meidän yhteinen projekti ja voit tehdä siihen muutoksia. (Älä kuitenkaan vielä tee)

8) Lataa uv (environment manager):

   Windows powershellissä: ```irm https://astral.sh/uv/install.ps1 | iex ```

   Linux ja macOS terminaalissa: ```curl -LsSf https://astral.sh/uv/install.sh | sh```

9) Lataa python virtuaaliympäristöön ja synkronisoi environment manager:
   ```
   uv python install
   
   uv sync --locked
   ```

# Workflow yleisesti:
 - Käytetään [git](https://git-scm.com/)tiä versionhallintajärjestelmänä ja koodin jakamisessa keskenämme
 - Käytetään pythonin riippuvuuksien ja virtuaalikoneen konfiguroinnissa eli environment managerina [uv](https://docs.astral.sh/uv/):ta
   
 - Tehdään projektissa vastuualueet projektin eri vaiheille jo suunnitteluvaiheessa
 - Jokainen työstää projektia omalla branchillaan ja kun projektissa on toimiva osakokonaisuus, yhdistetään branchit main-branchiin
 - Jos lisäät kirjaston projektii, niin kerro siitä muille! Tuo dependency muutos täytyy syncronisoida jokaisen erikseen. Komennot cheatsheetissä.
 - Tähän tarvitaan muutama git- ja uv-komento, jotka käydään läpi seuraavaksi

# GIT-workflow:

1) Alussa on ajettu git clone. Sitä ei enää tehdä.

2) Luo oma branch:

   ```git checkout -b uusi_branch main``` // tietyssä brancheissa tehdyt muutokset näkyy vain siinä branchissa

4) Kun olet saanut jotain aikaan, ne siirretään GitHubiin seuraavasti:
   
   I) ```git add muutettu_tiedosto1 muutettu_tiedosto2 ...```
   
   II) ```git status```
   
   II) ```git commit -m  "moromoro"```
   
   III) ```git push origin branchin_nimi```
   
6) 
    Jos tarvitset jonkun toisen vastuualueen koodia, täytyy ajaa:

   I) ```git switch oma_branch``` // vaihda omaan brachiin

   II) ```git pull --no-rebase origin haluttu_branch``` // hae viimeiset pushatut muutokset toisen branchista ja mergaa ne omaan

8) Merge main branchiin:
   
   Pidetään huolta, että merge main branchiin on aina yhdessä sovittu, eli käytännössä kun yksi vaihe projektia on saatu tehtyä. Tällä tavoin pystymme yrittää välttää merge conflicteja. Niiden ratkominen vie yleensä aikaa. Käytännössä kaikki pushaa omat branchinsa GitHubiin, tekee GitHubissa pull requestit mainiin ja ne hyväksytään manuaalisesti GitHubissa.

9) Kun siirrytään seuraavaan vaiheeseen, aletaan työstää mergattua mainia. Nyt se täytyy pullata:
 
    I) ```git switch main``` //vaihda mainiin

    II) ```git pull --no-rebase origin main``` // pullaa main


Tämän jälkeen iteroidaan vaiheita 2-6.

# Cheatsheet:
<table> <thead> <tr> <th>Situation</th> <th>Command</th> </tr> </thead> <tbody> <tr> <td>Clone repository (first time only)</td> <td><code>git clone &lt;ssh-link&gt;</code></td> </tr> <tr> <td>Install required Python version</td> <td><code>uv python install</code></td> </tr> <tr> <td>Set up / synchronize Python environment</td> <td><code>uv sync --locked</code></td> </tr> <tr> <td>Check local changes</td> <td><code>git status</code></td> </tr> <tr> <td>See actual unstaged changes</td> <td><code>git diff</code></td> </tr> <tr> <td>See staged changes</td> <td><code>git diff --staged</code></td> </tr> <tr> <td>List local branches</td> <td><code>git branch</code></td> </tr> <tr> <td>Create new branch and switch to it</td> <td><code>git checkout -b oma_branch main</code></td> </tr> <tr> <td>Stage specific files</td> <td><code>git add file1 file2 ...</code></td> </tr> <tr> <td>Commit changes</td> <td><code>git commit -m "Description"</code></td> </tr> <tr> <td>Push your branch to GitHub</td> <td><code>git push origin oma_branch</code></td> </tr> <tr> <td>Pull another person's branch into your own</td> <td> <code>git switch oma_branch</code><br> <code>git pull --no-rebase origin wanted_branch</code> </td> </tr> <tr> <td>Switch to main</td> <td><code>git switch main</code></td> </tr> <tr> <td>Update main from GitHub</td> <td><code>git pull --no-rebase origin main</code></td> </tr> <tr> <td>Merge updated main into your own branch</td> <td> <code>git switch oma_branch</code><br> <code>git merge main</code> </td> </tr> <tr> <td>Add a new Python library</td> <td><code>uv add library_name</code></td> </tr> <tr> <td>Add a specific library version</td> <td><code>uv add "library_name==version"</code></td> </tr> <tr> <td>Save and push dependency changes to GitHub</td> <td> <code>git add pyproject.toml uv.lock</code><br> <code>git commit -m "Add numpy"</code><br> <code>git push origin oma_branch</code> </td> </tr> <tr> <td>Synchronize dependencies after pulling changes</td> <td><code>uv sync --locked</code></td> </tr> <tr> <td>Remove a Python library</td> <td><code>uv remove library_name</code></td> </tr> </tbody> </table>

# Ohjeet koodin testaukseen:

- Kun teet funktioita tai luokkia pythonissa ja haluat testata niitä, kirjoita testi-koodi seuraavasti tiedoston loppuun:
 ```python
if __name__ == "__main__":
    testaa(funktio1())
```

  Tällöin python ajaa testikoodin vain kun ajat kyseisen tiedoston python-interpreterillä. Jos tiedostoa käytetään kirjastona toisessa ohjelmassa, testikoodia ei ajeta.
