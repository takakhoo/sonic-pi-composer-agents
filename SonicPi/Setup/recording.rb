live_loop :listen do
  use_real_time
  script = sync "/osc*/run-code"

  begin
    eval script[0]
    osc_send '127.0.0.1', script[2], '/feedback', script[1], 'OK: Code submitted successfully'
  rescue Exception => e
    osc_send '127.0.0.1', script[2], '/feedback', script[1], "ERROR: #{e.class}: #{e.message}"
  end
end
