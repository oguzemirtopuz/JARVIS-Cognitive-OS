KOTA VE VERİMLİLİK KURALLARI:

1. Görev karmaşıklığına göre model seç. Basit işler (küçük düzenleme,
   boilerplate, tekrar eden kod, basit UI değişikliği, syntax düzeltme)
   için en hızlı/en ucuz modeli kullan. Sadece çok dosyalı mimari
   kararlar, karmaşık debug, veya derin mantık gerektiren işlerde
   güçlü modele geç. Görev tamamlanınca hızlı modele geri dön.

2. Bana hangi model ile çalıştığını ve neden o modeli seçtiğini kısaca
   belirt, böylece kontrol edebileyim.

3. Context israfını önle. Tüm repoyu veya gereksiz dosyaları context'e
   çekme. Sadece göreve doğrudan ilgili dosyaları/fonksiyonları/satır
   aralıklarını oku. Emin değilsen önce hangi dosyalara bakman
   gerektiğini sor, sonra oku.

4. Büyük veya belirsiz bir görev geldiğinde direkt kod yazmaya başlama.
   Önce kısa bir plan/adım listesi çıkar, benim onayımı bekle, sonra
   uygula. Onaylanmamış varsayımlarla ilerleme.

5. Bir görev 3'ten fazla dosyayı etkiliyorsa veya 2 denemeden sonra
   hala çözülmediyse, bunu bana bildir ve gerekirse daha güçlü modele
   geçmemi öner — kendi başına sürekli deneme yaparak kota harcama.

6. Aynı hatayı 2'den fazla kez aynı şekilde çözmeye çalışma. Farklı bir
   yaklaşım dene veya bana durumu özetleyip yön iste.

DOĞRULUK VE HATA AZALTMA KURALLARI:

7. Kod yazdıktan sonra mutlaka kendi kendini doğrula: ilgili testi çalıştır,
   build/derleme kontrolü yap, veya tarayıcıda sonucu kontrol et. Doğrulama
   yapılmadan "tamamlandı" deme.

8. Varsayım yapman gerekiyorsa bunu açıkça belirt ("X olduğunu varsayıyorum,
   çünkü Y") — sessizce varsayımda bulunup ilerleme.

9. Emin olmadığın API, kütüphane sürümü veya dokümantasyon detayı varsa,
   tahmin etme; önce dosya içinde/bağımlılıklarda kontrol et veya bana sor.

10. Değişiklik yaptığın her dosyada, değişikliğin etkilediği diğer
    yerleri (import eden dosyalar, çağıran fonksiyonlar) kontrol et.
    Yan etkileri gözden kaçırma.

11. Kod yorumları ve commit mesajları Türkçe olsun; açıklamalarını da
    aynı dilde yap.

12. Silme, üzerine yazma, veritabanı/migration işlemleri gibi geri
    dönüşü zor adımlarda önce bana onay sor.

---
PROJE BAĞLAMI (otomatik tespit edildi):
- Proje adı: My_Jarvis_Project
- Proje türü: Python Script
- Ana dil ve framework: Python
- Klasör yapısı: .coverage, .env, .github, .gitignore, .jarvis_autostart, .pytest_cache, ai_studio_code.py, archive, ...
- Veritabanı / state management: yok

TEST VE DOĞRULAMA:
- Değişiklik sonrası çalıştırılacak komut: pytest
- Kritik dosyalar: .env

YASAKLAR:
- .env dosyasına asla dokunma (varsa)
- package.json/requirements.txt'e onaysız yeni bağımlılık ekleme
---