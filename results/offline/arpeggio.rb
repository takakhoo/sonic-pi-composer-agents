use_bpm 96
use_synth :piano
2.times do
  [60, 64, 67, 71, 69, 67, 64, 62].each do |n|
    play n, release: 0.6, amp: 0.4
    sleep 0.5
  end
end
