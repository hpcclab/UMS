class AsyncBlockingQueue<T> {
    private _promises: Promise<T>[]
    private _resolvers: ((t: T) => void)[]
    private _done: boolean

    constructor() {
        this._resolvers = []
        this._promises = []
        this._done = false
    }

    private _add() {
        this._promises.push(new Promise(resolve => {
            this._resolvers.push(resolve)
        }))
    }

    enqueue(t: T) {
        if (!this._resolvers.length) this._add()
        const resolve = this._resolvers.shift()!
        resolve(t)
    }

    dequeue() {
        if (!this._promises.length) this._add()
        return this._promises.shift()!
    }

    isEmpty() {
        return !this._promises.length
    }

    isBlocked() {
        return !!this._resolvers.length
    }

    get length() {
        return this._promises.length - this._resolvers.length
    }

    get done() {
        return this._done
    }

    set done(v: boolean) {
        this._done = v
    }
}

export {
    AsyncBlockingQueue
}
