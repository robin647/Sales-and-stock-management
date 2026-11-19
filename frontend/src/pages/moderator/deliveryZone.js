export const deliveryFees = { inside: 70, outside: 150 };

function placeNames(groups) {
  return new RegExp(`(?<![\\p{L}\\p{M}])(?:${groups.join("|").normalize("NFC")})(?![\\p{L}\\p{M}])`, "iu");
}

const outsideDhaka = placeNames([
  "Savar|Ashulia|Dhamrai|Keraniganj|Nawabganj|Dohar|Gazipur|Tongi|Narayanganj|Siddhirganj",
  "Sylhet|Ambarkhana|Habiganj|Sunamganj|Moulvibazar|Maulvibazar",
  "Chattogram|Chittagong|Cumilla|Comilla|Cox['’]?s Bazar|Feni|Noakhali|Chandpur|Lakshmipur|Brahmanbaria|Bandarban|Khagrachhari|Rangamati",
  "Rangpur|Dinajpur|Gaibandha|Kurigram|Lalmonirhat|Nilphamari|Panchagarh|Thakurgaon",
  "Rajshahi|Bogura|Bogra|Joypurhat|Naogaon|Natore|Chapainawabganj|Pabna|Sirajganj",
  "Khulna|Bagerhat|Chuadanga|Jessore|Jashore|Jhenaidah|Kushtia|Magura|Meherpur|Narail|Satkhira",
  "Barishal|Barisal|Barguna|Bhola|Jhalokati|Patuakhali|Pirojpur",
  "Mymensingh|Jamalpur|Netrokona|Netrakona|Sherpur|Tangail|Manikganj|Munshiganj|Narsingdi|Kishoreganj|Faridpur|Gopalganj|Madaripur|Rajbari|Shariatpur",
  "সিলেট|হবিগঞ্জ|সুনামগঞ্জ|মৌলভীবাজার|সাভার|আশুলিয়া|ধামরাই|কেরানীগঞ্জ|নবাবগঞ্জ|দোহার|গাজীপুর|টঙ্গী|নারায়ণগঞ্জ",
  "চট্টগ্রাম|কুমিল্লা|কক্সবাজার|ফেনী|নোয়াখালী|চাঁদপুর|লক্ষ্মীপুর|ব্রাহ্মণবাড়িয়া|বান্দরবান|খাগড়াছড়ি|রাঙ্গামাটি",
  "রংপুর|দিনাজপুর|গাইবান্ধা|কুড়িগ্রাম|লালমনিরহাট|নীলফামারী|পঞ্চগড়|ঠাকুরগাঁও",
  "রাজশাহী|বগুড়া|জয়পুরহাট|নওগাঁ|নাটোর|চাঁপাইনবাবগঞ্জ|পাবনা|সিরাজগঞ্জ",
  "খুলনা|বাগেরহাট|চুয়াডাঙ্গা|যশোর|ঝিনাইদহ|কুষ্টিয়া|মাগুরা|মেহেরপুর|নড়াইল|সাতক্ষীরা",
  "বরিশাল|বরগুনা|ভোলা|ঝালকাঠি|পটুয়াখালী|পিরোজপুর",
  "ময়মনসিংহ|জামালপুর|নেত্রকোণা|শেরপুর|টাঙ্গাইল|মানিকগঞ্জ|মুন্সিগঞ্জ|নরসিংদী|কিশোরগঞ্জ|ফরিদপুর|গোপালগঞ্জ|মাদারীপুর|রাজবাড়ী|শরীয়তপুর",
]);

const insideDhaka = placeNames([
  "Dhaka|Dacca|Dhanmondi|Mirpur|Uttara|Gulshan|Banani|Badda|Mohammadpur|Motijheel|Tejgaon|Malibagh|Rampura|Jatrabari|Bashundhara|Khilgaon|Farmgate|Azimpur|Lalbagh|Shahbag|Wari|Paltan",
  "ঢাকা|ধানমন্ডি|ধানমণ্ডি|মিরপুর|উত্তরা|গুলশান|বনানী|বাড্ডা|মোহাম্মদপুর|মতিঝিল|যাত্রাবাড়ী|বসুন্ধরা|খিলগাঁও",
]);

export function suggestDeliveryZone(address, area) {
  const location = `${area} ${address}`.normalize("NFC");
  if (outsideDhaka.test(location)) return "outside";
  return insideDhaka.test(location) ? "inside" : "";
}
