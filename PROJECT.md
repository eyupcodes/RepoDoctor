# RepoDoctor

## Konumlandırma

- **Kategori:** Developer Tools
- **Zorluk:** Kolay
- **Portföy amacı:** Tooling, static analysis ve developer experience tarafını gösterir.

## Amaç

Bir repository'nin temel sağlık, yapı ve güvenlik kontrollerini yapan CLI.

## Çözdüğü Problem

Küçük projelerde README, test, CI, license ve secret hygiene gibi temel kalite maddeleri sık atlanıyor.

## MVP Kapsamı

- Repository scanner
- README/LICENSE/.gitignore kontrolleri
- test klasörü tespiti
- CI tespiti
- env/secret risk pattern scan
- health score
- terminal report

## Önerilen Teknik Yığın

- Python 3.12+
- Typer
- Rich
- pathlib
- pytest

## Ölçülecek Metrikler

- health score
- passed checks
- warnings
- failures

## V1 Kabul Kriterleri

- Temiz bir makinede README adımlarıyla kurulabilmeli.
- Ana kullanım senaryosu tek komut veya kısa bir akışla çalışmalı.
- Kritik çekirdek davranışlar testlerle doğrulanmalı.
- Hatalı input kontrollü biçimde ele alınmalı.
- Örnek input ve örnek output repoda bulunmalı.
- GitHub Actions üzerinde temel test/lint akışı çalışmalı.
- Secret veya kişisel veri repository'ye girmemeli.

## Repo Yapısı

```text
repodoctor/
├── src/
├── tests/
├── examples/
├── docs/
├── .github/
│   └── workflows/
├── README.md
├── LICENSE
├── CHANGELOG.md
└── .gitignore
```

Gereksiz klasörler sırf şablon için açılmamalı.

## İlk Milestone'lar

### M1 — Foundation
- Proje skeleton
- CLI/app entrypoint
- Config modeli
- Test altyapısı
- CI

### M2 — Core
- MVP'nin ana fonksiyonları
- Temel hata yönetimi
- Örnek veri

### M3 — Quality
- Edge-case testleri
- README
- Example output
- Release hazırlığı

### M4 — Release
- `v0.1.0`
- GitHub topics
- Açıklama ve ekran görüntüsü
- Issues için başlangıç etiketleri

## Sonraki Geliştirmeler

- GitHub Actions integration
- SARIF output
- custom rules
- language-aware checks

## Bilinçli Olarak Yapılmayacaklar

- İlk sürümde gereksiz SaaS/account sistemi
- Sırf "AI project" görünmesi için zorunlu LLM entegrasyonu
- Kullanılmayan mikroservisler
- Erken optimizasyon
- Gizli/local sistemlerden proprietary mantık kopyalama

## GitHub Sunumu

README ilk ekranı şu dört şeyi hızlı göstermeli:

1. Bu araç ne yapıyor?
2. Neden var?
3. 30 saniyede nasıl denenir?
4. Örnek çıktı nasıl görünüyor?

Önerilen repository topics:

`developer-tools`, `developer-tools`, `portfolio`, `open-source`

## Commit Standardı

Örnek:

```text
feat: add core runner
test: cover invalid configuration
fix: handle timeout correctly
docs: add quick-start example
chore: configure CI
```

## Tamamlanmış Sayılma Şartı

Proje, yalnız kod yazıldığı için tamamlanmış sayılmaz. Aşağıdakiler olmadan `Done` değildir:

- Çalışan MVP
- Test
- README
- Example
- CI
- Release tag
