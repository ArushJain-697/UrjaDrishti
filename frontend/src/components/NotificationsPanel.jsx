import { useState, useEffect } from 'react'
import { Bell, X, Send, Phone, Mail, Save } from 'lucide-react'
import { client } from '../api/client'
import { useLanguage } from '../context/LanguageContext'

export default function NotificationsPanel({ isOpen, onClose }) {
  const { t } = useLanguage()
  const [waEnabled, setWaEnabled] = useState(false)
  const [waPhone, setWaPhone] = useState('')
  const [waThreshold, setWaThreshold] = useState('5')
  const [waStatus, setWaStatus] = useState('No alerts sent yet')

  const [emailEnabled, setEmailEnabled] = useState(false)
  const [emailAddress, setEmailAddress] = useState('')
  const [emailTime, setEmailTime] = useState('06:00')
  const [emailStatus, setEmailStatus] = useState('No briefing sent yet')

  const [isSendingWa, setIsSendingWa] = useState(false)
  const [isSendingEmail, setIsSendingEmail] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('urjadrishti_notification_settings')
    if (saved) {
      try {
        const d = JSON.parse(saved)
        setWaEnabled(d.waEnabled || false)
        setWaPhone(d.waPhone || '')
        setWaThreshold(d.waThreshold || '5')
        setEmailEnabled(d.emailEnabled || false)
        setEmailAddress(d.emailAddress || '')
        setEmailTime(d.emailTime || '06:00')
      } catch (e) {}
    }
  }, [])

  const saveSettings = () => {
    localStorage.setItem('urjadrishti_notification_settings', JSON.stringify({
      waEnabled, waPhone, waThreshold, emailEnabled, emailAddress, emailTime
    }))
    alert('Settings saved locally.')
  }

  const testWhatsApp = async () => {
    if (!waPhone) return alert('Enter phone number')
    setIsSendingWa(true)
    try {
      await client.post('/api/notifications/test-whatsapp', {
        phone: waPhone.replace('+', ''),
        message: 'UrjaDrishti Alert: System test successful. Confidence thresholds are active.'
      })
      setWaStatus(`Last alert sent: ${new Date().toLocaleTimeString()}`)
    } catch (err) {
      alert('WhatsApp test failed: ' + err.message)
    } finally {
      setIsSendingWa(false)
    }
  }

  const testEmail = async () => {
    if (!emailAddress) return alert('Enter email address')
    setIsSendingEmail(true)
    try {
      await client.post('/api/notifications/test-email', {
        email: emailAddress,
        subject: 'UrjaDrishti Daily Briefing',
        body: '<h3>UrjaDrishti Daily Forecast Briefing</h3><p>System test successful. Daily briefings will arrive at ' + emailTime + '.</p>'
      })
      setEmailStatus(`Last briefing sent: ${new Date().toLocaleTimeString()}`)
    } catch (err) {
      alert('Email test failed: ' + err.message)
    } finally {
      setIsSendingEmail(false)
    }
  }

  if (!isOpen) return null

  return (
    <>
      <div 
        className="fixed inset-0 z-[200] bg-black/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      <div className="fixed right-0 top-0 bottom-0 z-[210] w-[320px] transform bg-surface-bg border-l border-line shadow-2xl transition-transform duration-300 flex flex-col">
        
        <div className="flex items-center justify-between p-4 border-b border-line bg-base-bg">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-[#3b82f6]" />
            <h2 className="font-medium text-main-text text-lg">Alert Settings</h2>
          </div>
          <button onClick={onClose} className="text-muted-text hover:text-main-text transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-6">
          
          {/* WhatsApp Settings */}
          <div className="flex flex-col gap-3 rounded-lg border border-line bg-base-bg p-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-[#25D366]"></div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-medium text-main-text">
                <Phone className="h-4 w-4 text-[#25D366]" />
                WhatsApp Alert
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" checked={waEnabled} onChange={(e) => setWaEnabled(e.target.checked)} />
                <div className="w-9 h-5 bg-[#3a3d52] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#25D366]"></div>
              </label>
            </div>
            
            <div className="flex flex-col gap-1.5 mt-2">
              <label className="text-xs text-muted-text">Phone (+91 format)</label>
              <input type="text" value={waPhone} onChange={e=>setWaPhone(e.target.value)} disabled={!waEnabled} placeholder="+919876543210" className="rounded-md border border-line bg-surface-bg px-2.5 py-1.5 text-sm text-main-text outline-none focus:border-[#25D366] disabled:opacity-50" />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-muted-text">Alert me when confidence drops below</label>
              <select value={waThreshold} onChange={e=>setWaThreshold(e.target.value)} disabled={!waEnabled} className="rounded-md border border-line bg-surface-bg px-2.5 py-1.5 text-sm text-main-text outline-none disabled:opacity-50">
                <option value="3">3 (Severe)</option>
                <option value="4">4 (High)</option>
                <option value="5">5 (Medium)</option>
                <option value="6">6 (Low)</option>
              </select>
            </div>

            <button onClick={testWhatsApp} disabled={!waEnabled || isSendingWa} className="mt-1 flex w-full items-center justify-center gap-2 rounded-md bg-[#25D366]/10 py-1.5 text-sm font-medium text-[#25D366] hover:bg-[#25D366]/20 transition-colors disabled:opacity-50">
              <Send className="h-3.5 w-3.5" />
              {isSendingWa ? 'Sending...' : 'Test WhatsApp Now'}
            </button>
            <div className="text-[10px] text-faint-text text-center italic mt-1">{waStatus}</div>
          </div>

          {/* Email Settings */}
          <div className="flex flex-col gap-3 rounded-lg border border-line bg-base-bg p-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-[#3b82f6]"></div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-medium text-main-text">
                <Mail className="h-4 w-4 text-[#3b82f6]" />
                Morning Briefing
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} />
                <div className="w-9 h-5 bg-[#3a3d52] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#3b82f6]"></div>
              </label>
            </div>
            
            <div className="flex flex-col gap-1.5 mt-2">
              <label className="text-xs text-muted-text">Email Address</label>
              <input type="email" value={emailAddress} onChange={e=>setEmailAddress(e.target.value)} disabled={!emailEnabled} placeholder="duty@kredl.gov.in" className="rounded-md border border-line bg-surface-bg px-2.5 py-1.5 text-sm text-main-text outline-none focus:border-[#3b82f6] disabled:opacity-50" />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-muted-text">Daily Delivery Time (IST)</label>
              <select value={emailTime} onChange={e=>setEmailTime(e.target.value)} disabled={!emailEnabled} className="rounded-md border border-line bg-surface-bg px-2.5 py-1.5 text-sm text-main-text outline-none disabled:opacity-50">
                <option value="05:30">05:30</option>
                <option value="06:00">06:00</option>
                <option value="06:30">06:30</option>
                <option value="07:00">07:00</option>
              </select>
            </div>

            <button onClick={testEmail} disabled={!emailEnabled || isSendingEmail} className="mt-1 flex w-full items-center justify-center gap-2 rounded-md bg-[#3b82f6]/10 py-1.5 text-sm font-medium text-[#3b82f6] hover:bg-[#3b82f6]/20 transition-colors disabled:opacity-50">
              <Send className="h-3.5 w-3.5" />
              {isSendingEmail ? 'Sending...' : 'Test Email Now'}
            </button>
            <div className="text-[10px] text-faint-text text-center italic mt-1">{emailStatus}</div>
          </div>

        </div>
        
        <div className="p-4 border-t border-line bg-base-bg">
          <button onClick={saveSettings} className="flex w-full items-center justify-center gap-2 rounded-md bg-[#3b82f6] py-2 text-sm font-semibold text-white hover:bg-[#2563eb] transition-colors">
            <Save className="h-4 w-4" />
            Save Preferences
          </button>
        </div>

      </div>
    </>
  )
}
