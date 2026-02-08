type Handler = (data: any) => void

class WSClient {
  private ws?: WebSocket
  private handlers = new Map<string, Set<Handler>>()

  connect(url: string) {
    if (this.ws) return

    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      const set = this.handlers.get(msg.type)

      set?.forEach(fn => fn(msg))
    }
  }

  send(data: any) {
    this.ws?.send(JSON.stringify(data))
  }

  on(type: string, handler: Handler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }

    this.handlers.get(type)!.add(handler)
  }

  off(type: string, handler: Handler) {
    this.handlers.get(type)?.delete(handler)
  }

  close() {
    this.ws?.close()
    this.ws = undefined
  }
}

export default new WSClient()
