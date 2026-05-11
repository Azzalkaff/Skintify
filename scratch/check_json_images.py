import json

with open('data/products_sociolla.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

products = data.get('products', [])
print(f'Total produk di JSON: {len(products)}')
print()

# Cek 3 sampel
for i, p in enumerate(products[:3]):
    print(f'--- Produk {i+1} ---')
    for key in ['product_name', 'brand', 'slug', 'image_url', 'url', 'category', 'average_rating']:
        val = p.get(key, 'TIDAK ADA')
        if isinstance(val, str) and len(val) > 80:
            val = val[:80] + '...'
        print(f'  {key}: {val}')
    print()

# Hitung yang punya image_url
has_image = sum(1 for p in products if p.get('image_url'))
has_slug = sum(1 for p in products if p.get('slug'))
print(f'Produk dengan image_url: {has_image}/{len(products)}')
print(f'Produk dengan slug: {has_slug}/{len(products)}')

# Tampilkan contoh image_url
for p in products[:5]:
    img = p.get('image_url', '')
    if img:
        print(f'  Contoh image_url: {img[:100]}')
        break
