from faker import Faker

fake = Faker("ko_KR")  # 한국 데이터

print(fake.name())
print(fake.email())
print(fake.phone_number())
print(fake.address())